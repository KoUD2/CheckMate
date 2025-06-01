import logging
import json
from yookassa import Payment
from yookassa.domain.notification import WebhookNotification
from datetime import datetime, timedelta
import asyncio

# Импортируем функцию обновления подписки из API сервиса
from services.api_service import update_user_subscription

# Настройка логирования
logger = logging.getLogger(__name__)

# Заглушка для хранения подписок (в реальном проекте должно быть в БД)
USER_SUBSCRIPTIONS = {}

# Сохраняем ссылку на объект бота
_bot = None

def setup_bot(bot):
    """Устанавливает объект бота для отправки сообщений"""
    global _bot
    _bot = bot
    logger.info("Бот установлен для отправки уведомлений о платежах")

class SubscriptionPeriod:
    ONE_MONTH = 30  # дней

def get_all_active_subscriptions():
    """Возвращает все активные подписки (для отладки)"""
    return USER_SUBSCRIPTIONS

async def process_payment_notification(webhook_data: dict) -> bool:
    """
    Обрабатывает уведомления о платежах от ЮKassa.
    
    Args:
        webhook_data: Данные вебхука от ЮKassa
        
    Returns:
        bool: True если обработка успешна, False в противном случае
    """
    try:
        logger.info(f"🔄 Обработка webhook данных: {webhook_data}")
        
        # Проверяем тип события
        event_type = webhook_data.get("event")
        if not event_type:
            logger.error("❌ Отсутствует поле event в webhook данных")
            return False
            
        logger.info(f"📧 Тип события: {event_type}")

        # Обрабатываем только успешные платежи
        if event_type != "payment.succeeded":
            logger.info(f"ℹ️ Событие {event_type} не требует обработки")
            return True

        # Извлекаем данные о платеже
        payment_object = webhook_data.get("object", {})
        payment_id = payment_object.get("id")
        payment_status = payment_object.get("status")
        payment_metadata = payment_object.get("metadata", {})
        user_id = payment_metadata.get("user_id")

        logger.info(f"💳 Payment ID: {payment_id}")
        logger.info(f"📊 Payment Status: {payment_status}")
        logger.info(f"👤 User ID из metadata: {user_id}")

        if not user_id:
            logger.error("❌ Отсутствует user_id в metadata платежа")
            return False

        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            logger.error(f"❌ Некорректный user_id: {user_id}")
            return False

        logger.info(f"🎯 Начинаем обработку успешного платежа для пользователя {user_id}")

        # Обновляем подписку через API
        logger.info(f"🌐 Обновляем подписку через API...")
        api_success = await update_user_subscription(user_id, 30)
        
        if api_success:
            logger.info(f"✅ Подписка через API успешно обновлена для пользователя {user_id}")
        else:
            logger.error(f"❌ Не удалось обновить подписку через API для пользователя {user_id}")

        # Активируем подписку локально
        logger.info(f"🏠 Активируем подписку локально...")
        activate_subscription(user_id, 30)
        logger.info(f"✅ Подписка локально активирована для пользователя {user_id}")

        # Отправляем уведомление пользователю
        logger.info(f"📤 Отправляем уведомление пользователю...")
        await notify_user_payment_success(user_id)
        logger.info(f"✅ Уведомление отправлено пользователю {user_id}")

        logger.info(f"🎉 Платеж успешно обработан для пользователя {user_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка при обработке уведомления о платеже: {e}")
        logger.error(f"🔍 Тип ошибки: {type(e).__name__}")
        return False

def activate_subscription(user_id: int, period: int = SubscriptionPeriod.ONE_MONTH):
    """
    Активирует подписку для пользователя.
    
    Args:
        user_id: ID пользователя в Telegram
        period: Период подписки в днях
    """
    # Расчет даты истечения подписки
    expiry_date = datetime.now() + timedelta(days=period)
    
    # Сохраняем информацию о подписке (в реальном проекте - в БД)
    USER_SUBSCRIPTIONS[user_id] = {
        "expiry_date": expiry_date,
        "is_active": True,
        "purchase_date": datetime.now()
    }
    
    logger.info(f"Активирована подписка для пользователя {user_id} до {expiry_date}")
    logger.info(f"Текущие активные подписки: {USER_SUBSCRIPTIONS}")

async def notify_user_payment_success(user_id: int):
    """
    Отправляет пользователю уведомление об успешной оплате.
    
    Args:
        user_id: ID пользователя в Telegram
    """
    if not _bot:
        logger.warning(f"Невозможно отправить уведомление пользователю {user_id}: бот не инициализирован")
        return
    
    try:
        # Получаем информацию о подписке
        subscription = USER_SUBSCRIPTIONS.get(user_id)
        
        if not subscription:
            logger.error(f"Ошибка при отправке уведомления: нет данных о подписке для пользователя {user_id}")
            return
        
        # Форматируем дату окончания подписки
        expiry_date_str = subscription["expiry_date"].strftime("%d.%m.%Y")
        days_left = (subscription["expiry_date"] - datetime.now()).days
        
        # Отправляем сообщение
        await _bot.send_message(
            chat_id=user_id, 
            text=f"✅ Оплата прошла успешно!\n\nВаша подписка активирована до {expiry_date_str}.\n"
                 f"Осталось дней: {days_left}.\n\nСпасибо за поддержку бота!"
        )
        logger.info(f"Отправлено уведомление о успешной оплате пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о успешном платеже: {e}")

async def notify_user_payment_canceled(user_id: int):
    """
    Отправляет пользователю уведомление об отмене платежа.
    
    Args:
        user_id: ID пользователя в Telegram
    """
    if not _bot:
        logger.warning(f"Невозможно отправить уведомление пользователю {user_id}: бот не инициализирован")
        return
    
    try:
        # Отправляем сообщение
        await _bot.send_message(
            chat_id=user_id, 
            text="❌ Платеж отменен.\n\nВы можете попробовать снова, отправив команду /subscription."
        )
        logger.info(f"Отправлено уведомление об отмене платежа пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления об отмене платежа: {e}") 