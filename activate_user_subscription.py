import asyncio
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

from services.payment_callbacks import activate_subscription, get_all_active_subscriptions
from services.payment_service import SubscriptionStatus, get_subscription_status

USER_ID = 1054927360

def activate_for_user():
    """Активирует подписку для пользователя из скриншота"""
    logger.info(f"Активация подписки для пользователя {USER_ID}")
    
    activate_subscription(USER_ID)
    
    all_subscriptions = get_all_active_subscriptions()
    logger.info(f"Текущие активные подписки: {all_subscriptions}")
    
    status = get_subscription_status(USER_ID)
    logger.info(f"Статус подписки пользователя {USER_ID}: {status}")
    
    if status["status"] == SubscriptionStatus.ACTIVE:
        logger.info(f"✅ Подписка успешно активирована! Осталось дней: {status['days_left']}")
    else:
        logger.error("❌ Не удалось активировать подписку")

if __name__ == "__main__":
    activate_for_user()
    logger.info("Запустите webhook_server.py и выполните /subscription в боте")
    logger.info("Или откройте http://localhost:8080/activate/subscription?user_id=1054927360") 