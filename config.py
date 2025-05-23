import logging
import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# API ключи (обязательные для продакшена)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OCR_API_KEY = os.getenv("OCR_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Проверяем наличие обязательных переменных
required_vars = {
    "GEMINI_API_KEY": GEMINI_API_KEY,
    "OCR_API_KEY": OCR_API_KEY,
    "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# OCR настройки
OCR_API_URL = os.getenv("OCR_API_URL", "https://api.ocr.space/parse/image")

# YooKassa настройки
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

# Webhook настройки
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8443"))

# API Base URL
API_BASE_URL = os.getenv("API_BASE_URL", "https://checkmateai.ru")

# Состояния разговора
CHOOSE_TASK, TASK_DESCRIPTION, GRAPH_IMAGE, TASK_SOLUTION, CHECKING, SHOW_ANALYSIS = range(6)

def setup_logging():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
        level=logging.INFO,
        handlers=[
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__) 