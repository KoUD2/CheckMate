import requests
import os
import logging
from config import OCR_API_KEY, OCR_API_URL

logger = logging.getLogger(__name__)

async def process_image_ocr(image_path):
    """Обработка изображения через OCR.space API с Engine 2"""
    try:
        logger.info(f"Отправка изображения в OCR.space API: {image_path}")
        
        # Подготовка данных для отправки
        with open(image_path, 'rb') as f:
            payload = {
                'isOverlayRequired': 'false',
                'language': 'eng',
                'OCREngine': '2',  # Используем Engine 2 как требуется
                'scale': 'true'    # Масштабирование для лучшего распознавания
            }
            
            files = {
                'file': (os.path.basename(image_path), f, 'image/jpeg')
            }
            
            headers = {
                'apikey': OCR_API_KEY
            }
            
            # Отправка запроса к API
            logger.info(f"Отправка запроса к OCR.space API")
            response = requests.post(OCR_API_URL, 
                                   files=files, 
                                   data=payload, 
                                   headers=headers)
            
            # Проверка успешности запроса
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Получен ответ от OCR.space API: {result}")
                
                # Проверка на наличие ошибок в ответе
                if result.get('IsErroredOnProcessing', False):
                    error_message = result.get('ErrorMessage', 'Unknown error')
                    logger.error(f"Ошибка OCR API: {error_message}")
                    return f"Ошибка распознавания: {error_message}"
                
                # Извлечение распознанного текста
                parsed_results = result.get('ParsedResults', [])
                if parsed_results:
                    parsed_text = parsed_results[0].get('ParsedText', '')
                    logger.info(f"Распознанный текст (первые 100 символов): {parsed_text[:100]}...")
                    return parsed_text
                else:
                    logger.warning("Результаты OCR отсутствуют в ответе")
                    return "Не удалось распознать текст на изображении"
            else:
                logger.error(f"Ошибка запроса к OCR API: {response.status_code} - {response.text}")
                return f"Ошибка запроса к OCR API: {response.status_code}"
                
    except Exception as e:
        logger.error(f"Исключение при обработке изображения через OCR API: {e}")
        return f"Ошибка при обработке изображения: {str(e)}" 