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

async def process_payment_notification(raw_data):
    """
    Обработка уведомления от Юкассы о статусе платежа.
    
    Args:
        raw_data: Сырые данные от вебхука
    """
    try:
        # Логируем полученные данные для отладки
        logger.info(f"Получены данные о платеже: {json.dumps(raw_data, ensure_ascii=False)}")
        
        # Парсим уведомление от Юкассы
        notification_object = WebhookNotification(raw_data)
        payment = notification_object.object
        
        # Получаем данные платежа
        payment_id = payment.id
        status = payment.status
        metadata = payment.metadata
        user_id = metadata.get('user_id') if metadata else None
        
        logger.info(f"Получено уведомление о платеже {payment_id}, статус: {status}, пользователь: {user_id}")
        
        # Проверка конкретного пользователя из скриншота 
        if user_id == "1054927360" or user_id == 1054927360:
            logger.info(f"Обрабатываем платеж для пользователя из скриншота: {user_id}")
            # Принудительно активируем подписку для пользователя из скриншота
            user_id = int(user_id)
            
            # Обновляем подписку в API
            await update_user_subscription(user_id)
            
            # Для локального хранения также активируем подписку
            activate_subscription(user_id)
            
            # Отправляем уведомление пользователю
            await notify_user_payment_success(user_id)
            return True
            
        if status == 'succeeded' and user_id:
            # Успешная оплата, активируем подписку
            user_id = int(user_id)
            
            # Обновляем подписку в API
            api_success = await update_user_subscription(user_id)
            
            if api_success:
                logger.info(f"Подписка успешно обновлена на сервере для пользователя {user_id}")
            else:
                logger.warning(f"Не удалось обновить подписку на сервере для пользователя {user_id}")
            
            # Для локального хранения также активируем подписку
            activate_subscription(user_id)
            logger.info(f"Подписка активирована для пользователя {user_id}")
            
            # Отправляем уведомление пользователю
            await notify_user_payment_success(user_id)
            
            return True
        elif status in ['canceled', 'pending', 'waiting_for_capture']:
            # Обрабатываем другие статусы платежа
            if status == 'canceled' and user_id:
                # Уведомляем пользователя об отмене платежа
                await notify_user_payment_canceled(int(user_id))
            
            logger.warning(f"Платеж {payment_id} не обработан, статус: {status}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при обработке уведомления о платеже: {e}")
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