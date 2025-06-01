import logging
import asyncio
import re
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler
from services.ocr_service import process_image_ocr
from services.gemini_service import check_with_gemini
from services.api_service import register_user, decrement_user_free_checks, can_user_proceed_with_check, send_essay_result, send_table_task_result
from services.image_service import convert_image_to_base64
from utils.task37_parser import parse_task37_description, extract_criterion_scores_and_comments
from utils.task38_parser import parse_task38_description, extract_criterion_scores_and_comments_38
from config import CHOOSE_TASK, TASK_DESCRIPTION, GRAPH_IMAGE, TASK_SOLUTION, CHECKING, SHOW_ANALYSIS

# Настройка логирования
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Первое сообщение бота с выбором задания"""
    keyboard = [
        [InlineKeyboardButton("Задание 37", callback_data="37")],
        [InlineKeyboardButton("Задание 38", callback_data="38")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери задание", reply_markup=reply_markup)
    
    return CHOOSE_TASK

async def task_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора задания"""
    query = update.callback_query
    await query.answer()
    
    # Сохраняем номер задания
    context.user_data['task_number'] = query.data
    
    # Отправляем первое сообщение о выбранном задании
    await query.edit_message_text(f"Задание {query.data}")
    
    # Отправляем второе сообщение с просьбой о формулировке
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="📄Пришли формулировку задания"
    )
    
    return TASK_DESCRIPTION

async def get_task_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение формулировки задания от пользователя"""
    # Сохраняем формулировку задания
    context.user_data['task_description'] = update.message.text
    
    # Проверяем номер задания
    if context.user_data.get('task_number') == "38":
        await update.message.reply_text(
            "📊 Пришли, пожалуйста, изображение графика"
        )
        return GRAPH_IMAGE
    else:
        await update.message.reply_text(
            "📝Теперь пришли свою работу (решение задания)"
        )
        return TASK_SOLUTION

async def get_graph_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение изображения графика для задания 38"""
    # Проверяем, есть ли изображение
    photo = update.message.photo
    
    if photo:
        # Берем самое большое фото (последнее в списке)
        photo_file = photo[-1]
        photo_id = photo_file.file_id
        
        # Сохраняем ID фото для последующей обработки
        context.user_data['graph_image_id'] = photo_id
        logger.info(f"Получено изображение графика для задания 38, file_id: {photo_id}")
        
        # Отправляем сообщение о обработке
        processing_message = await update.message.reply_text("🔍 Обрабатываю изображение графика...")
        
        try:
            # Получаем файл из Telegram
            file = await context.bot.get_file(photo_id)
            file_path = f"temp_{photo_id}.jpg"
            
            # Скачиваем файл
            await file.download_to_drive(file_path)
            logger.info(f"Изображение графика сохранено в {file_path}")
            
            # Загружаем изображение в MinIO
            await processing_message.edit_text("🔍 Конвертирую изображение в base64...")
            image_base64 = convert_image_to_base64(file_path)
            
            if image_base64:
                # Сохраняем base64 изображения в контексте пользователя
                context.user_data['table_image_url'] = image_base64
                logger.info(f"Изображение успешно конвертировано в base64 (длина: {len(image_base64)} символов)")
            else:
                logger.warning("Не удалось конвертировать изображение в base64")
                context.user_data['table_image_url'] = ""
            
            # Обрабатываем изображение через OCR.space API
            await processing_message.edit_text("🔍 Распознаю текст на изображении...")
            ocr_result = await process_image_ocr(file_path)
            
            # Сохраняем результат OCR в контексте пользователя
            context.user_data['graph_ocr_text'] = ocr_result
            
            # Удаляем временный файл
            try:
                os.remove(file_path)
                logger.info(f"Временный файл {file_path} удален")
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл: {e}")
            
            # Обновляем сообщение о результате обработки
            await processing_message.edit_text("✅ Изображение графика обработано")
            
            # Запрашиваем решение
            await update.message.reply_text(
                "📝Теперь пришли свою работу (решение задания)"
            )
            return TASK_SOLUTION
            
        except Exception as e:
            logger.error(f"Ошибка при обработке изображения: {e}")
            await processing_message.edit_text("❌ Произошла ошибка при обработке изображения")
            
            # Все равно продолжаем диалог
            await update.message.reply_text(
                "📝Теперь пришли свою работу (решение задания)"
            )
            return TASK_SOLUTION
    else:
        # Если пользователь отправил сообщение без фото, просим еще раз
        await update.message.reply_text(
            "Пожалуйста, отправь изображение графика. Если у тебя нет изображения, отправь любую картинку, и я продолжу."
        )
        return GRAPH_IMAGE

async def get_task_solution(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение решения задания от пользователя"""
    # Сохраняем решение
    context.user_data['task_solution'] = update.message.text
    
    # Проверяем, может ли пользователь продолжить с проверкой
    user_id = update.effective_user.id
    check_permission = await can_user_proceed_with_check(user_id)
    
    if not check_permission.get("can_proceed", False):
        # Если пользователь не может продолжить, отправляем сообщение с причиной
        reason = check_permission.get("reason", "Неизвестная ошибка")
        FreeChecksLeft = check_permission.get("FreeChecksLeft", 0)
        
        await update.message.reply_text(
            f"❌ {reason}\n\n"
            f"Бесплатных проверок осталось: {FreeChecksLeft}\n\n"
            f"Для продолжения необходимо оформить подписку. Используйте команду /subscription"
        )
        return ConversationHandler.END
    
    # Сообщение о начале проверки
    status_message = await update.message.reply_text(
        "✨Теперь немного подожди, скоро случится магия..."
    )
    
    try:
        # Сообщаем о начале проверки
        await status_message.edit_text("🔍 Анализирую твою работу... (0%)")
        
        # Проверяем задание с помощью Gemini
        logger.info("Начинаем проверку задания")
        
        # Создаем обработчик статуса для отправки сообщений о прогрессе
        async def update_status(text):
            try:
                await status_message.edit_text(text)
            except Exception as e:
                logger.error(f"Ошибка при обновлении статуса: {e}")
        
        # Получаем номер задания для определения возвращаемых данных
        task_number = context.user_data.get('task_number')
        
        if task_number == "37":
            # Для задания 37 функция возвращает дополнительную информацию
            score, feedback, extra_info = await check_with_gemini(user_data=context.user_data, status_callback=update_status)
            
            # Отправляем результат на бэкенд для задания 37
            try:
                # Парсим задание для извлечения email, subject и questions_theme
                task_description = context.user_data.get('task_description', '')
                parsed_data = parse_task37_description(task_description)
                
                # Извлекаем комментарии по критериям
                scores = extra_info.get('scores', [0, 0, 0])
                responses = extra_info.get('responses', ['', '', ''])
                comments = extract_criterion_scores_and_comments(responses, scores)
                
                # Формируем данные для отправки на бэкенд
                essay_data = {
                    "comments": comments,
                    "email": parsed_data.get('email', ''),
                    "essay": context.user_data.get('task_solution', ''),
                    "k1": scores[0],
                    "k2": scores[1],
                    "k3": scores[2],
                    "questions_theme": parsed_data.get('questions_theme', ''),
                    "subject": parsed_data.get('subject', '')
                }
                
                # Отправляем на бэкенд
                logger.info("Отправляем результаты проверки задания 37 на бэкенд")
                backend_success = await send_essay_result(essay_data)
                
                if backend_success:
                    logger.info("Результаты успешно отправлены на бэкенд")
                else:
                    logger.warning("Не удалось отправить результаты на бэкенд")
                    
            except Exception as e:
                logger.error(f"Ошибка при отправке результатов на бэкенд: {e}")
        elif task_number == "38":
            # Для задания 38 функция возвращает дополнительную информацию
            score, feedback, extra_info = await check_with_gemini(user_data=context.user_data, status_callback=update_status)
            
            # Отправляем результат на бэкенд для задания 38
            try:
                # Парсим задание для извлечения opinion и problem
                task_description = context.user_data.get('task_description', '')
                parsed_data = parse_task38_description(task_description)
                
                # Извлекаем комментарии по критериям (для задания 38 - 5 критериев)
                scores = extra_info.get('scores', [0, 0, 0, 0, 0])
                responses = extra_info.get('responses', ['', '', '', '', ''])
                comments = extract_criterion_scores_and_comments_38(responses, scores)
                
                # Получаем base64 данные изображения
                table_image_base64 = context.user_data.get('table_image_url', '')
                
                # Формируем данные для отправки на бэкенд
                table_task_data = {
                    "comments": comments,
                    "essay": context.user_data.get('task_solution', ''),
                    "k1": scores[0],
                    "k2": scores[1],
                    "k3": scores[2],
                    "k4": scores[3],
                    "k5": scores[4],
                    "opinion": parsed_data.get('opinion', ''),
                    "problem": parsed_data.get('problem', ''),
                    "table_image": table_image_base64
                }
                
                # Отправляем на бэкенд
                logger.info("Отправляем результаты проверки задания 38 на бэкенд")
                backend_success = await send_table_task_result(table_task_data)
                
                if backend_success:
                    logger.info("Результаты задания 38 успешно отправлены на бэкенд")
                else:
                    logger.warning("Не удалось отправить результаты задания 38 на бэкенд")
                    
            except Exception as e:
                logger.error(f"Ошибка при отправке результатов задания 38 на бэкенд: {e}")
        else:
            # Для других заданий стандартный вызов
            score, feedback = await check_with_gemini(user_data=context.user_data, status_callback=update_status)
        
        # Уменьшаем счетчик бесплатных проверок после успешной проверки
        decrement_success = await decrement_user_free_checks(user_id)
        if decrement_success:
            logger.info(f"Счетчик бесплатных проверок для пользователя {user_id} успешно уменьшен")
        else:
            logger.warning(f"Не удалось уменьшить счетчик бесплатных проверок для пользователя {user_id}")
        
        # Удаляем сообщение о статусе
        await status_message.delete()
        
        # Сохраняем обратную связь в контексте пользователя для дальнейшего использования
        context.user_data['feedback'] = feedback
        
        # Создаем клавиатуру с кнопкой "Подробный анализ"
        keyboard = [
            [InlineKeyboardButton("📝 Подробный анализ", callback_data="show_analysis")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем результат проверки с кнопкой
        logger.info(f"Проверка завершена, отправляем результат с оценкой: {score}")
        
        # Извлекаем информацию о баллах по критериям из feedback, если это задание 38 или 37
        criteria_info = ""
        
        if task_number in ["37", "38"]:
            # Ищем блок с баллами по критериям в начале отзыва
            criteria_pattern = r'Баллы по критериям:\n(.*?)\n\nОбщий балл:'
            criteria_match = re.search(criteria_pattern, feedback, re.DOTALL)
            
            if criteria_match:
                criteria_info = f"\n\n{criteria_match.group(1)}"
        
        await update.message.reply_text(
            f"Проверка завершена! Твоя оценка: {score} баллов.{criteria_info}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return SHOW_ANALYSIS
        
    except Exception as e:
        # В случае ошибки отправляем сообщение об этом
        error_msg = f"Ошибка при проверке задания: {e}"
        logger.error(error_msg)
        await update.message.reply_text(
            f"Произошла ошибка при проверке. Детали ошибки: {str(e)}"
        )
        
        return ConversationHandler.END

async def show_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать детальный анализ после нажатия на кнопку"""
    query = update.callback_query
    await query.answer()
    
    # Получаем сохраненный анализ
    feedback = context.user_data.get('feedback', "Детальный анализ недоступен")
    
    logger.info("Отправляем подробный анализ по запросу пользователя")
    
    # Разделяем текст по абзацам
    paragraphs = feedback.split('\n\n')
    
    # Группируем абзацы в сообщения, не превышающие 4000 символов
    messages = []
    current_message = ""
    
    for paragraph in paragraphs:
        # Если текущее сообщение станет слишком длинным при добавлении абзаца
        if len(current_message + paragraph + "\n\n") > 3800:  # Небольшой запас для заголовка
            # Если текущий абзац сам по себе слишком длинный
            if len(paragraph) > 3800:
                # Разбиваем длинный абзац по предложениям
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                temp_paragraph = ""
                
                for sentence in sentences:
                    if len(temp_paragraph + sentence + " ") > 3800:
                        if current_message:
                            messages.append(current_message)
                        current_message = temp_paragraph.strip()
                        temp_paragraph = sentence + " "
                    else:
                        temp_paragraph += sentence + " "
                
                if current_message:
                    messages.append(current_message)
                current_message = temp_paragraph.strip()
            else:
                # Добавляем заполненное сообщение в список и начинаем новое
                messages.append(current_message)
                current_message = paragraph + "\n\n"
        else:
            # Добавляем абзац к текущему сообщению
            current_message += paragraph + "\n\n"
    
    # Добавляем последнее сообщение, если оно не пустое
    if current_message.strip():
        messages.append(current_message)
    
    # Проверка на пустые сообщения
    messages = [msg for msg in messages if msg.strip()]
    
    if messages:
        # Отправляем первую часть, заменяя сообщение с кнопкой
        await query.edit_message_text(
            text=f"Подробный анализ твоей работы:\n\n{messages[0]}",
            parse_mode='Markdown'
        )
        
        # Отправляем остальные части как новые сообщения
        last_message_id = None
        for i, message in enumerate(messages[1:], 2):
            try:
                sent_message = await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"{message}",
                    parse_mode='Markdown'
                )
                last_message_id = sent_message.message_id
                # Короткая пауза между сообщениями для предотвращения ограничений Telegram
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Ошибка при отправке части анализа {i}: {e}")
        
        # Добавляем кнопки лайка и дизлайка к последнему сообщению
        # Если было только одно сообщение, то редактируем его
        if last_message_id:
            # Создаем клавиатуру с кнопками лайк/дизлайк
            rating_keyboard = [
                [
                    InlineKeyboardButton("👍", callback_data="rating_like"),
                    InlineKeyboardButton("👎", callback_data="rating_dislike")
                ]
            ]
            rating_markup = InlineKeyboardMarkup(rating_keyboard)
            
            # Добавляем кнопки к последнему сообщению
            await context.bot.edit_message_reply_markup(
                chat_id=query.message.chat_id,
                message_id=last_message_id,
                reply_markup=rating_markup
            )
        else:
            # Если был только один абзац, добавляем кнопки к нему
            rating_keyboard = [
                [
                    InlineKeyboardButton("👍", callback_data="rating_like"),
                    InlineKeyboardButton("👎", callback_data="rating_dislike")
                ]
            ]
            rating_markup = InlineKeyboardMarkup(rating_keyboard)
            
            # Обновляем первое сообщение, добавляя кнопки
            await query.edit_message_reply_markup(reply_markup=rating_markup)
    else:
        # Если анализ недоступен
        await query.edit_message_text(
            text="Анализ недоступен"
        )
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена диалога"""
    await update.message.reply_text('Проверка отменена')
    return ConversationHandler.END

async def new_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начать выбор нового задания"""
    # Получаем информацию о пользователе
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Регистрируем пользователя в системе
    await register_user(user_id, username)
    
    # Очищаем данные пользователя
    context.user_data.clear()
    
    # Повторяем логику из начальной функции
    keyboard = [
        [InlineKeyboardButton("Задание 37", callback_data="37")],
        [InlineKeyboardButton("Задание 38", callback_data="38")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери задание", reply_markup=reply_markup)
    
    return CHOOSE_TASK

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отправить фидбек разработчику"""
    await update.message.reply_text(
        "Вы можете отправить отзыв или сообщить о проблеме разработчику\n"
        "https://t.me/KonstUd"
    )
    
    # Остаемся в текущем состоянии
    return ConversationHandler.END 