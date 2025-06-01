import re
import time
import logging
import os
import asyncio
import aiofiles
import google.generativeai as genai
from requests.exceptions import Timeout, ConnectionError
from config import GEMINI_API_KEY

# Настройка логирования
logger = logging.getLogger(__name__)

# Конфигурация Gemini API
genai.configure(api_key=GEMINI_API_KEY)

async def check_with_gemini(user_data: dict, status_callback=None) -> tuple:
    """Проверка задания через Gemini API"""
    task_number = user_data['task_number']
    task_description = user_data['task_description']
    task_solution = user_data['task_solution']
    
    logger.info(f"Начинаем проверку задания №{task_number}")
    logger.info(f"Формулировка задания: {task_description[:50]}...")
    logger.info(f"Решение: {task_solution[:50]}...")
    
    # Проверяем наличие изображения графика для задания 38
    has_graph_image = 'graph_image_id' in user_data and task_number == "38"
    if has_graph_image:
        logger.info(f"Задание 38 включает изображение графика (ID: {user_data['graph_image_id']})")
    
    # Проверяем наличие OCR-текста из графика для задания 38
    graph_ocr_text = user_data.get('graph_ocr_text', '')
    if graph_ocr_text and task_number == "38":
        logger.info(f"Имеется OCR-текст графика длиной {len(graph_ocr_text)} символов")
    
    # Создание модели
    logger.info("Инициализация модели Gemini 2.5 Flash Preview")
    model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
    
    # Настройка параметров генерации
    generation_config = {
        "temperature": 0.4,
        "top_p": 0.95,
        "top_k": 0,
        "max_output_tokens": 8192,
    }
    
    try:
        if task_number == "37":
            # Проверка количества слов для задания 37
            if status_callback:
                await status_callback("📊 Подсчёт количества слов...")
            
            # Подсчет слов в решении
            words = re.findall(r'\b\w+\b', task_solution)
            word_count = len(words)
            logger.info(f"Количество слов в тексте: {word_count}")
            
            original_word_count = word_count
            truncation_notice = ""
            
            # Если количество слов превышает 154, обрезаем текст
            if word_count > 154:
                logger.info(f"Обрезаем текст с {word_count} до 154 слов")
                # Получаем первые 154 слова
                truncated_words = words[:154]
                # Преобразуем список слов в текст, сохраняя пробелы и пунктуацию
                pattern = r'\b(' + '|'.join(re.escape(word) for word in truncated_words) + r')\b'
                matches = list(re.finditer(pattern, task_solution))
                if matches and len(matches) >= 154:
                    # Находим позицию последнего слова
                    last_match = matches[153]
                    end_pos = last_match.end()
                    task_solution = task_solution[:end_pos]
                else:
                    # Резервный вариант, если регулярное выражение не сработало
                    task_solution = ' '.join(truncated_words)
                
                word_count = 154
                truncation_notice = f"⚠️ Ваш текст был обрезан до 154 слов для проверки (исходное количество слов: {original_word_count}).\n\n"
                logger.info(f"Текст обрезан. Новая длина: {len(task_solution)} символов")
            
            # Если меньше 90 слов, сразу возвращаем 0 баллов
            if word_count < 90:
                logger.warning(f"Недостаточное количество слов: {word_count} < 90. Выставляем 0 баллов.")
                error_msg = f"Количество слов в тексте ({word_count}) меньше минимального требуемого (90).\n\nВ соответствии с критериями оценивания за такую работу выставляется 0 баллов."
                # Для задания 37 возвращаем дополнительную информацию для отправки на бэкенд
                extra_info = {
                    "scores": [0, 0, 0],
                    "responses": ["", "", ""]
                }
                return 0, error_msg, extra_info
            
            # Для задания 37 используем последовательные промпты из файлов
            logger.info("Используем последовательные промпты для задания 37")
            all_responses = []
            scores = [0, 0, 0]  # Оценки по трем критериям
            
            # Статус проверки: начинаем
            if status_callback:
                await status_callback("🔍 Анализирую твою работу... (0%)")
            
            # Проходим по всем трем промптам
            for i in range(1, 4):
                # Обновляем статус
                if status_callback:
                    await status_callback(f"🔍 Анализирую твою работу... Шаг {i}/3 ({i*33}%)")
                
                logger.info(f"Обработка промпта {i}/3")
                prompt_path = f"prompts/prompt{i}.txt"
                
                if not os.path.exists(prompt_path):
                    logger.error(f"Файл промпта не найден: {prompt_path}")
                    error_msg = f"Файл промпта не найден: {prompt_path}"
                    extra_info = {
                        "scores": [0, 0, 0],
                        "responses": ["", "", ""]
                    }
                    return "Ошибка проверки", error_msg, extra_info
                
                async with aiofiles.open(prompt_path, "r", encoding="utf-8") as file:
                    prompt_template = await file.read()
                
                # Подставляем данные пользователя в промпт
                prompt = prompt_template.replace("[Текст задания из сообщения пользователя в телеграм]", task_description)
                prompt = prompt.replace("[Текст емейла из сообщения пользователя в телеграм]", task_solution)
                
                logger.info(f"Промпт {i} подготовлен, длина: {len(prompt)} символов")
                logger.info(f"Начало промпта {i}: {prompt[:100]}...")
                
                # Отправляем запрос к Gemini с механизмом повторных попыток
                logger.info(f"Отправка запроса к Gemini (промпт {i})")
                start_time = time.time()
                
                # Обновляем статус
                if status_callback:
                    await status_callback(f"🤖 Отправляю запрос к AI... Шаг {i}/3 ({i*33}%)")
                
                max_retries = 3
                retry_delay = 5  # секунд
                
                for attempt in range(max_retries):
                    try:
                        # Обновляем статус при повторной попытке
                        if attempt > 0 and status_callback:
                            await status_callback(f"🔄 Повторная попытка {attempt}/{max_retries}... Шаг {i}/3 ({i*33}%)")
                        
                        response = model.generate_content(
                            prompt,
                            generation_config=generation_config
                        )
                        
                        elapsed_time = time.time() - start_time
                        logger.info(f"Получен ответ от Gemini (промпт {i}), время выполнения: {elapsed_time:.2f} секунд")
                        logger.info(f"Начало ответа: {response.text[:100]}...")
                        all_responses.append(response.text)
                        break  # Успешно получили ответ
                        
                    except (Timeout, ConnectionError) as e:
                        if attempt < max_retries - 1:
                            delay = retry_delay * (attempt + 1)
                            logger.warning(f"Таймаут при запросе к Gemini (промпт {i}), попытка {attempt+1}/{max_retries}. Ожидание {delay} секунд...")
                            await asyncio.sleep(delay)
                        else:
                            logger.error(f"Не удалось получить ответ от Gemini после {max_retries} попыток: {str(e)}")
                            raise
                    except Exception as e:
                        logger.error(f"Ошибка при обработке промпта {i}: {str(e)}")
                        if attempt < max_retries - 1:
                            delay = retry_delay * (attempt + 1)
                            logger.warning(f"Повторная попытка {attempt+1}/{max_retries} через {delay} секунд...")
                            await asyncio.sleep(delay)
                        else:
                            raise
                
                # Обновляем статус после получения ответа
                if status_callback:
                    await status_callback(f"📊 Анализирую ответ... Шаг {i}/3 ({i*33}%)")
                
                # Извлекаем оценку в зависимости от номера промпта
                response_text = response.text
                
                if i == 1:
                    # Для первого промпта ищем "Итоговый балл: X" в различных форматах
                    logger.info("Извлечение оценки из первого промпта (критерий 1)")
                    # Проверяем несколько вариантов форматирования
                    score_matches = re.search(r'Итоговый балл:?\s*(\d+)(?:\s*балл|\.|\s|$)', response_text)
                    if not score_matches:
                        score_matches = re.search(r'итоговый балл:?\s*(\d+)(?:\s*балл|\.|\s|$)', response_text)
                    if not score_matches:
                        score_matches = re.search(r'ИТОГОВЫЙ БАЛЛ:?\s*(\d+)(?:\s*балл|\.|\s|$)', response_text)
                    if not score_matches:
                        # Ищем любой балл в последнем абзаце итоговой оценки
                        last_section = response_text.split("ИТОГОВАЯ ОЦЕНКА")[-1] if "ИТОГОВАЯ ОЦЕНКА" in response_text else response_text
                        score_matches = re.search(r'(\d+)\s*балл', last_section)
                        
                    if score_matches:
                        scores[0] = int(score_matches.group(1))
                        logger.info(f"Найдена оценка по критерию 1: {scores[0]}")
                    else:
                        logger.warning("Не удалось найти оценку в первом промпте. Устанавливаем значение по умолчанию: 1")
                        scores[0] = 1  # Значение по умолчанию
                
                elif i == 2:
                    # Для второго промпта ищем "Балл: X" в различных форматах
                    logger.info("Извлечение оценки из второго промпта (критерий 2)")
                    # Проверяем несколько вариантов форматирования
                    score_matches = re.search(r'Балл:?\s*(\d+)(?:\s*балл|\.|\s|$)', response_text)
                    if not score_matches:
                        score_matches = re.search(r'получает\s*\*\*(\d+)\s*балл', response_text)
                    if not score_matches:
                        score_matches = re.search(r'оценка:?\s*(\d+)(?:\s*балл|\.|\s|$)', response_text)
                    
                    if score_matches:
                        scores[1] = int(score_matches.group(1))
                        logger.info(f"Найдена оценка по критерию 2: {scores[1]}")
                    else:
                        logger.warning("Не удалось найти оценку во втором промпте. Устанавливаем значение по умолчанию: 1")
                        scores[1] = 1  # Значение по умолчанию
                
                elif i == 3:
                    # Для третьего промпта ищем "Общий балл: X" в различных форматах
                    logger.info("Извлечение оценки из третьего промпта (критерий 3)")
                    
                    # Сначала проверяем блок ИТОГОВАЯ ОЦЕНКА, если он есть
                    if "ИТОГОВАЯ ОЦЕНКА" in response_text:
                        logger.info("Найден блок ИТОГОВАЯ ОЦЕНКА в ответе для критерия 3")
                        итоговая_оценка_блок = response_text.split("ИТОГОВАЯ ОЦЕНКА")[1].split("\n\n")[0]
                        общий_балл_match = re.search(r'Общий балл:?\s*(\d+)', итоговая_оценка_блок)
                        if общий_балл_match:
                            scores[2] = int(общий_балл_match.group(1))
                            logger.info(f"Найдена оценка по критерию 3 в блоке ИТОГОВАЯ ОЦЕНКА: {scores[2]}")
                            continue
                    
                    # Проверяем несколько вариантов форматирования
                    score_matches = re.search(r'Общий балл:?\s*(\d+)(?:\s*балл|\.|\s|$)', response_text)
                    if not score_matches:
                        score_matches = re.search(r'общий балл:?\s*(\d+)(?:\s*балл|\.|\s|$)', response_text)
                    if not score_matches:
                        score_matches = re.search(r'ОБЩИЙ БАЛЛ:?\s*(\d+)(?:\s*балл|\.|\s|$)', response_text)
                    
                    if score_matches:
                        scores[2] = int(score_matches.group(1))
                        logger.info(f"Найдена оценка по критерию 3: {scores[2]}")
                    else:
                        logger.warning("Не удалось найти оценку в третьем промпте. Устанавливаем значение по умолчанию: 1")
                        scores[2] = 1  # Значение по умолчанию
            
            # Проверяем первый критерий - если 0, то вся работа оценивается в 0 баллов
            if scores[0] == 0:
                logger.info("Оценка по первому критерию равна 0, выставляем 0 за всю работу")
                final_score = 0
                scores_info = truncation_notice
                scores_info += f"Так как оценка по первому критерию (Решение коммуникативной задачи) равна 0, за всю работу выставляется 0 баллов.\n\n"
                scores_info += f"Баллы по критериям:\n1. Решение коммуникативной задачи: {scores[0]}\n2. Организация текста: {scores[1]}\n3. Языковое оформление: {scores[2]}\n\nОбщий балл: {final_score}\n\n---\n\n"
            else:
                # Суммируем баллы по всем критериям
                final_score = sum(scores)
                logger.info(f"Баллы по критериям: {scores}. Итоговая сумма: {final_score}")
                scores_info = truncation_notice
                scores_info += f"Баллы по критериям:\n1. Решение коммуникативной задачи: {scores[0]}\n2. Организация текста: {scores[1]}\n3. Языковое оформление: {scores[2]}\n\nОбщий балл: {final_score}\n\n---\n\n"
            
            # Обновляем статус: завершено
            if status_callback:
                await status_callback("✅ Проверка завершена! Подготавливаю результаты...")
            
            # Объединяем все ответы с явным обозначением разделов
            combined_response = scores_info
            combined_response += "📝 КРИТЕРИЙ 1: РЕШЕНИЕ КОММУНИКАТИВНОЙ ЗАДАЧИ\n\n" + all_responses[0] + "\n\n"
            combined_response += "🔠 КРИТЕРИЙ 2: ОРГАНИЗАЦИЯ ТЕКСТА\n\n" + all_responses[1] + "\n\n"
            combined_response += "📚 КРИТЕРИЙ 3: ЯЗЫКОВОЕ ОФОРМЛЕНИЕ\n\n" + all_responses[2]
            
            # Для задания 37 возвращаем дополнительную информацию для отправки на бэкенд
            extra_info = {
                "scores": scores,
                "responses": all_responses
            }
            
            return final_score, combined_response, extra_info
        
        elif task_number == "38":
            # Для задания 38 используем последовательные промпты из файлов (всего 5)
            logger.info("Используем последовательные промпты для задания 38 (всего 5)")
            all_responses = []
            scores = [0, 0, 0, 0, 0]  # Оценки по пяти критериям
            
            # Проверка количества слов для задания 38
            if status_callback:
                await status_callback("📊 Подсчёт количества слов...")
            
            # Подсчет слов в решении
            words = re.findall(r'\b\w+\b', task_solution)
            word_count = len(words)
            logger.info(f"Количество слов в тексте: {word_count}")
            
            # Если меньше 180 слов, сразу возвращаем 0 баллов
            if word_count < 180:
                logger.warning(f"Недостаточное количество слов для задания 38: {word_count} < 180. Выставляем 0 баллов.")
                return 0, f"Количество слов в тексте ({word_count}) меньше минимального требуемого (180).\n\nВ соответствии с критериями оценивания за такую работу выставляется 0 баллов."
            
            original_word_count = word_count
            truncation_notice = ""
            
            # Если количество слов превышает 275, обрезаем текст
            if word_count > 275:
                logger.info(f"Обрезаем текст с {word_count} до 275 слов")
                # Получаем первые 275 слов
                truncated_words = words[:275]
                # Преобразуем список слов в текст, сохраняя пробелы и пунктуацию
                pattern = r'\b(' + '|'.join(re.escape(word) for word in truncated_words) + r')\b'
                matches = list(re.finditer(pattern, task_solution))
                if matches and len(matches) >= 275:
                    # Находим позицию последнего слова
                    last_match = matches[274]
                    end_pos = last_match.end()
                    task_solution = task_solution[:end_pos]
                else:
                    # Резервный вариант, если регулярное выражение не сработало
                    task_solution = ' '.join(truncated_words)
                
                word_count = 275
                truncation_notice = f"⚠️ Ваш текст был обрезан до 275 слов для проверки (исходное количество слов: {original_word_count}).\n\n"
                logger.info(f"Текст обрезан. Новая длина: {len(task_solution)} символов")
            
            # Статус проверки: начинаем
            if status_callback:
                await status_callback("🔍 Анализирую твою работу... (0%)")
            
            # Проходим по всем пяти промптам
            for i in range(1, 6):
                # Обновляем статус
                if status_callback:
                    await status_callback(f"🔍 Анализирую твою работу... Шаг {i}/5 ({i*20}%)")
                
                logger.info(f"Обработка промпта {i}/5 для задания 38")
                prompt_path = f"prompts/prompt38_{i}.txt"
                
                if not os.path.exists(prompt_path):
                    logger.error(f"Файл промпта не найден: {prompt_path}")
                    return "Ошибка проверки", f"Файл промпта не найден: {prompt_path}"
                
                async with aiofiles.open(prompt_path, "r", encoding="utf-8") as file:
                    prompt_template = await file.read()
                
                # Подготавливаем информацию о графике, если есть
                graph_info = ""
                if has_graph_image and graph_ocr_text:
                    graph_info = f"\n\nРаспознанный текст с графика:\n{graph_ocr_text}"
                
                # Подставляем данные пользователя в промпт
                prompt = prompt_template.replace("[Текст задания из сообщения пользователя в телеграм]", task_description)
                prompt = prompt.replace("[Текст описания графика из сообщения пользователя в телеграм]", task_solution)
                prompt = prompt.replace("[Распознанный текст графика]", graph_info)
                
                logger.info(f"Промпт {i} для задания 38 подготовлен, длина: {len(prompt)} символов")
                logger.info(f"Начало промпта {i}: {prompt[:100]}...")
                
                # Отправляем запрос к Gemini с механизмом повторных попыток
                logger.info(f"Отправка запроса к Gemini (промпт {i} для задания 38)")
                start_time = time.time()
                
                # Обновляем статус
                if status_callback:
                    await status_callback(f"🤖 Отправляю запрос к AI... Шаг {i}/5 ({i*20}%)")
                
                max_retries = 3
                retry_delay = 5  # секунд
                
                for attempt in range(max_retries):
                    try:
                        # Обновляем статус при повторной попытке
                        if attempt > 0 and status_callback:
                            await status_callback(f"🔄 Повторная попытка {attempt}/{max_retries}... Шаг {i}/5 ({i*20}%)")
                        
                        response = model.generate_content(
                            prompt,
                            generation_config=generation_config
                        )
                        
                        elapsed_time = time.time() - start_time
                        logger.info(f"Получен ответ от Gemini (промпт {i} для задания 38), время выполнения: {elapsed_time:.2f} секунд")
                        logger.info(f"Начало ответа: {response.text[:100]}...")
                        all_responses.append(response.text)
                        break  # Успешно получили ответ
                        
                    except (Timeout, ConnectionError) as e:
                        if attempt < max_retries - 1:
                            delay = retry_delay * (attempt + 1)
                            logger.warning(f"Таймаут при запросе к Gemini (промпт {i} для задания 38), попытка {attempt+1}/{max_retries}. Ожидание {delay} секунд...")
                            await asyncio.sleep(delay)
                        else:
                            logger.error(f"Не удалось получить ответ от Gemini после {max_retries} попыток: {str(e)}")
                            raise
                    except Exception as e:
                        logger.error(f"Ошибка при обработке промпта {i} для задания 38: {str(e)}")
                        if attempt < max_retries - 1:
                            delay = retry_delay * (attempt + 1)
                            logger.warning(f"Повторная попытка {attempt+1}/{max_retries} через {delay} секунд...")
                            await asyncio.sleep(delay)
                        else:
                            raise
                
                # Обновляем статус после получения ответа
                if status_callback:
                    await status_callback(f"📊 Анализирую ответ... Шаг {i}/5 ({i*20}%)")
                
                # Извлекаем оценку в зависимости от номера промпта
                response_text = response.text
                logger.info(f"Начинаем извлечение оценки для критерия {i}")
                logger.info(f"Конец ответа для критерия {i}: ...{response_text[-200:]}")
                
                # Сначала ищем в блоке ИТОГОВАЯ ОЦЕНКА
                score_found = False
                if "ИТОГОВАЯ ОЦЕНКА" in response_text:
                    logger.info(f"Найден блок ИТОГОВАЯ ОЦЕНКА для критерия {i}")
                    # Извлекаем блок ИТОГОВАЯ ОЦЕНКА
                    итоговая_блоки = response_text.split("ИТОГОВАЯ ОЦЕНКА")
                    if len(итоговая_блоки) > 1:
                        # Берем текст после "ИТОГОВАЯ ОЦЕНКА"
                        итоговая_текст = итоговая_блоки[1]
                        
                        # Удаляем пустые строки в начале
                        итоговая_текст = итоговая_текст.lstrip('\n\r\t ')
                        
                        # Берем до следующего двойного переноса или конца (но не менее 100 символов для поиска балла)
                        итоговая_секция_части = итоговая_текст.split("\n\n")
                        итоговая_секция = итоговая_секция_части[0]
                        
                        # Если первая часть слишком короткая, берем больше текста
                        if len(итоговая_секция) < 50 and len(итоговая_секция_части) > 1:
                            итоговая_секция = итоговая_секция + "\n\n" + итоговая_секция_части[1]
                        
                        logger.info(f"Секция ИТОГОВАЯ ОЦЕНКА для критерия {i}: {итоговая_секция}")
                        
                        # Ищем "Балл: X" в этой секции
                        балл_match = re.search(r'Балл:?\s*(\d+)', итоговая_секция)
                        if балл_match:
                            scores[i-1] = int(балл_match.group(1))
                            logger.info(f"Найдена оценка для критерия {i} в блоке ИТОГОВАЯ ОЦЕНКА: {scores[i-1]}")
                            score_found = True
                        else:
                            logger.warning(f"Не найден паттерн 'Балл: X' в секции ИТОГОВАЯ ОЦЕНКА для критерия {i}")
                else:
                    logger.warning(f"Не найден блок ИТОГОВАЯ ОЦЕНКА для критерия {i}")
                
                # Если не нашли в блоке ИТОГОВАЯ ОЦЕНКА, используем общие паттерны
                if not score_found:
                    logger.info(f"Поиск оценки общими паттернами для критерия {i}")
                    # Общий шаблон для извлечения оценки из разных промптов
                    score_patterns = [
                        r'Балл:?\s*(\d+)(?:\s*балл|\s*из\s*\d+|\.|\s|$)',
                        r'Итоговый балл:?\s*(\d+)(?:\s*балл|\s*из\s*\d+|\.|\s|$)',
                        r'Финальный балл:?\s*(\d+)(?:\s*балл|\s*из\s*\d+|\.|\s|$)',
                        r'ОЦЕНКА:?\s*(\d+)(?:\s*балл|\s*из\s*\d+|\.|\s|$)',
                        r'Оценка:?\s*(\d+)(?:\s*балл|\s*из\s*\d+|\.|\s|$)',
                        r'получает\s*\*\*(\d+)\s*балл'
                    ]
                    
                    # Извлекаем оценку с использованием разных паттернов
                    for pattern in score_patterns:
                        score_matches = re.search(pattern, response_text)
                        if score_matches:
                            scores[i-1] = int(score_matches.group(1))
                            logger.info(f"Найдена оценка для критерия {i} паттерном '{pattern}': {scores[i-1]}")
                            score_found = True
                            break
                
                if not score_found:
                    logger.warning(f"Не удалось найти оценку в промпте {i} для задания 38. Устанавливаем значение по умолчанию: 1")
                    scores[i-1] = 1  # Значение по умолчанию
            
            # Проверяем первый критерий - если 0, то вся работа оценивается в 0 баллов
            if scores[0] == 0:
                logger.info("Оценка по первому критерию равна 0, выставляем 0 за всю работу")
                final_score = 0
                scores_info = truncation_notice  # Добавляем уведомление об обрезке текста, если оно есть
                scores_info += f"Так как оценка по первому критерию (Решение коммуникативной задачи) равна 0, за всю работу выставляется 0 баллов.\n\n"
                scores_info += f"Баллы по критериям:\n"
                scores_info += f"1. Решение коммуникативной задачи: {scores[0]}\n"
                scores_info += f"2. Организация текста: {scores[1]}\n"
                scores_info += f"3. Языковое оформление (лексика): {scores[2]}\n"
                scores_info += f"4. Языковое оформление (грамматика): {scores[3]}\n"
                scores_info += f"5. Орфография и пунктуация: {scores[4]}\n\n"
                scores_info += f"Общий балл: {final_score}\n\n---\n\n"
            else:
                # Суммируем баллы по всем критериям
                final_score = sum(scores)
                logger.info(f"Баллы по критериям (задание 38): {scores}. Итоговая сумма: {final_score}")
            
                # Формируем сводку баллов
                scores_info = truncation_notice  # Добавляем уведомление об обрезке текста, если оно есть
                scores_info += f"Баллы по критериям:\n"
                scores_info += f"1. Решение коммуникативной задачи: {scores[0]}\n"
                scores_info += f"2. Организация текста: {scores[1]}\n"
                scores_info += f"3. Языковое оформление (лексика): {scores[2]}\n"
                scores_info += f"4. Языковое оформление (грамматика): {scores[3]}\n"
                scores_info += f"5. Орфография и пунктуация: {scores[4]}\n\n"
                scores_info += f"Общий балл: {final_score}\n\n---\n\n"
            
            # Обновляем статус: завершено
            if status_callback:
                await status_callback("✅ Проверка завершена! Подготавливаю результаты...")
            
            # Объединяем все ответы с явным обозначением разделов
            combined_response = scores_info
            combined_response += "�� КРИТЕРИЙ 1: РЕШЕНИЕ КОММУНИКАТИВНОЙ ЗАДАЧИ\n\n" + all_responses[0] + "\n\n"
            combined_response += "🔠 КРИТЕРИЙ 2: ОРГАНИЗАЦИЯ ТЕКСТА\n\n" + all_responses[1] + "\n\n"
            combined_response += "📚 КРИТЕРИЙ 3: ЯЗЫКОВОЕ ОФОРМЛЕНИЕ (ЛЕКСИКА)\n\n" + all_responses[2] + "\n\n"
            combined_response += "📖 КРИТЕРИЙ 4: ЯЗЫКОВОЕ ОФОРМЛЕНИЕ (ГРАММАТИКА)\n\n" + all_responses[3] + "\n\n"
            combined_response += "✏️ КРИТЕРИЙ 5: ОРФОГРАФИЯ И ПУНКТУАЦИЯ\n\n" + all_responses[4]
            
            # Формируем extra_info для задания 38
            extra_info = {
                "scores": scores,
                "responses": all_responses
            }
            
            return final_score, combined_response, extra_info
            
        else:
            # Для других заданий используем стандартный промпт
            logger.info(f"Используем стандартный промпт для задания {task_number}")
            prompt = f"""
            Проверь, пожалуйста, решение задания №{task_number}.
            
            Формулировка задания:
            {task_description}
            
            Решение:
            {task_solution}
            
            Оцени решение по 10-балльной шкале. В ответе укажи только количество баллов (число от 0 до 10).
            """
            
            logger.info(f"Отправка запроса к Gemini")
            start_time = time.time()
            
            max_retries = 3
            retry_delay = 5  # секунд
            
            for attempt in range(max_retries):
                try:
                    response = model.generate_content(
                        prompt,
                        generation_config=generation_config
                    )
                    
                    elapsed_time = time.time() - start_time
                    logger.info(f"Получен ответ от Gemini, время выполнения: {elapsed_time:.2f} секунд")
                    break  # Успешно получили ответ
                    
                except (Timeout, ConnectionError) as e:
                    if attempt < max_retries - 1:
                        delay = retry_delay * (attempt + 1)
                        logger.warning(f"Таймаут при запросе к Gemini, попытка {attempt+1}/{max_retries}. Ожидание {delay} секунд...")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"Не удалось получить ответ от Gemini после {max_retries} попыток: {str(e)}")
                        raise
                except Exception as e:
                    logger.error(f"Ошибка при запросе к Gemini: {str(e)}")
                    if attempt < max_retries - 1:
                        delay = retry_delay * (attempt + 1)
                        logger.warning(f"Повторная попытка {attempt+1}/{max_retries} через {delay} секунд...")
                        await asyncio.sleep(delay)
                    else:
                        raise
            
            response_text = response.text.strip()
            logger.info(f"Ответ Gemini: {response_text}")
            
            # Извлекаем оценку
            score_matches = re.search(r'(\d+(?:\.\d+)?)\s*(?:балл|из|\/|\s*10)', response_text)
            if score_matches:
                score = score_matches.group(1)
            else:
                # Если не найдена оценка в формате "X баллов", ищем просто цифру в начале
                score_matches = re.search(r'^\s*(\d+(?:\.\d+)?)', response_text)
                if score_matches:
                    score = score_matches.group(1)
                else:
                    # Берем первую встречающуюся цифру
                    digits = re.findall(r'\b(\d+(?:\.\d+)?)\b', response_text)
                    if digits:
                        score = digits[0]
                    else:
                        score = "7"  # Значение по умолчанию, если не удалось найти число
            
            logger.info(f"Извлечена оценка: {score}")
            return score, response_text
            
    except Exception as e:
        error_msg = f"Ошибка при использовании Gemini API: {e}"
        logger.error(error_msg)
        
        # Обновляем статус при ошибке
        if status_callback:
            await status_callback("❌ Произошла ошибка при проверке")
        
        return "Ошибка проверки", error_msg 