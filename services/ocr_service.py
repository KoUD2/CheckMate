import aiohttp
import aiofiles
import os
import logging
from config import OCR_API_KEY, OCR_API_URL

logger = logging.getLogger(__name__)

async def process_image_ocr(image_path):
    """Обработка изображения через OCR.space API с Engine 2"""
    try:
        logger.info(f"Отправка изображения в OCR.space API: {image_path}")
        
        # Подготовка данных для отправки
        async with aiofiles.open(image_path, 'rb') as f:
            file_data = await f.read()
            
            data = aiohttp.FormData()
            data.add_field('isOverlayRequired', 'false')
            data.add_field('language', 'eng')
            data.add_field('OCREngine', '2')  # Используем Engine 2 как требуется
            data.add_field('scale', 'true')    # Масштабирование для лучшего распознавания
            data.add_field('file', file_data, filename=os.path.basename(image_path), content_type='image/jpeg')
            
            headers = {
                'apikey': OCR_API_KEY
            }
            
            # Отправка запроса к API
            logger.info(f"Отправка запроса к OCR.space API")
            async with aiohttp.ClientSession() as session:
                async with session.post(OCR_API_URL, data=data, headers=headers) as response:
                    
                    # Проверка успешности запроса
                    if response.status == 200:
                        result = await response.json()
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
                        response_text = await response.text()
                        logger.error(f"Ошибка запроса к OCR API: {response.status} - {response_text}")
                        return f"Ошибка запроса к OCR API: {response.status}"
                
    except Exception as e:
        logger.error(f"Исключение при обработке изображения через OCR API: {e}")
        return f"Ошибка при обработке изображения: {str(e)}" 