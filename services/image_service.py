import logging
import base64
import aiofiles
from typing import Optional

# Настройка логирования
logger = logging.getLogger(__name__)

async def convert_image_to_base64(image_path: str) -> Optional[str]:
    """
    Конвертирует изображение в base64 строку в формате data:image/jpeg;base64,...
    
    Args:
        image_path: Путь к локальному файлу изображения
        
    Returns:
        str: Строка в формате data:image/jpeg;base64,{base64_data} или None в случае ошибки
    """
    try:
        logger.info(f"Конвертируем изображение {image_path} в base64")
        
        # Читаем изображение как бинарные данные
        async with aiofiles.open(image_path, 'rb') as image_file:
            image_data = await image_file.read()
        
        # Конвертируем в base64
        base64_data = base64.b64encode(image_data).decode('utf-8')
        
        # Формируем строку в нужном формате
        base64_string = f"data:image/jpeg;base64,{base64_data}"
        
        logger.info(f"Изображение успешно конвертировано в base64 (длина: {len(base64_string)} символов)")
        
        return base64_string
        
    except Exception as e:
        logger.error(f"Ошибка при конвертации изображения в base64: {e}")
        return None 