import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Для работы с API Юкассы
from yookassa import Configuration, Payment

# Импортируем хранилище подписок из payment_callbacks
from services.payment_callbacks import USER_SUBSCRIPTIONS, get_all_active_subscriptions

# Настройка логирования
logger = logging.getLogger(__name__)

# Настройка API Юкассы
YOOKASSA_API_KEY = "test_oqu9vEtaRtFtuDFnCyUDblip-i9Ceb-EV5NDtQ4PHVg"
YOOKASSA_SHOP_ID = "1035098"  # Используем тестовый магазин
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_API_KEY

class SubscriptionStatus:
    EXPIRED = "expired"
    ACTIVE = "active"

def get_subscription_status(user_id: int) -> Dict[str, Any]:
    """
    Получить статус подписки пользователя.
    
    Проверяет наличие активной подписки в хранилище подписок.
    """
    # Логируем все активные подписки для отладки
    all_subscriptions = get_all_active_subscriptions()
    logger.info(f"Проверка подписки для пользователя {user_id}. Все подписки: {all_subscriptions}")
    
    # Проверяем, есть ли пользователь в базе подписок
    if user_id in USER_SUBSCRIPTIONS:
        subscription = USER_SUBSCRIPTIONS[user_id]
        logger.info(f"Найдена информация о подписке для пользователя {user_id}: {subscription}")
        
        # Проверяем, активна ли подписка
        if subscription["is_active"]:
            expiry_date = subscription["expiry_date"]
            
            # Проверяем, не истек ли срок подписки
            if expiry_date > datetime.now():
                # Вычисляем сколько дней осталось
                days_left = (expiry_date - datetime.now()).days
                
                return {
                    "status": SubscriptionStatus.ACTIVE,
                    "expiry_date": expiry_date,
                    "days_left": days_left
                }
            else:
                logger.info(f"Подписка для пользователя {user_id} истекла {expiry_date}")
        else:
            logger.info(f"Подписка для пользователя {user_id} неактивна")
    else:
        logger.info(f"Пользователь {user_id} не найден в базе подписок")
    
    # По умолчанию: подписка истекла
    return {
        "status": SubscriptionStatus.EXPIRED,
        "expiry_date": None,
        "days_left": 0
    }

def format_subscription_message(subscription_data: Dict[str, Any]) -> str:
    """Форматирует сообщение о статусе подписки"""
    if subscription_data["status"] == SubscriptionStatus.ACTIVE:
        if subscription_data["days_left"] == 0:
            return "Ваша подписка истекает сегодня."
        elif subscription_data["days_left"] == 1:
            return "До истечения подписки остался 1 день."
        elif subscription_data["days_left"] < 5:
            return f"До истечения подписки осталось: {subscription_data['days_left']} дня."
        else:
            return f"До истечения подписки осталось: {subscription_data['days_left']} дней."
    else:
        return "Ваша подписка истекла."

async def create_payment_link(user_id: int, amount: float = 149.00) -> str:
    """
    Создаёт ссылку для оплаты через Юкассу.
    
    Использует реальный API Юкассы с тестовым аккаунтом для создания платежа.
    """
    try:
        # Генерируем уникальный идентификатор платежа
        idempotence_key = str(uuid.uuid4())
        
        # Создаем платеж в Юкассе
        payment = Payment.create({
            "amount": {
                "value": amount,
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/checkmate_ai_bot"  # URL для возврата после оплаты - замените на ваш юзернейм бота
            },
            "capture": True,
            "description": f"Оплата подписки пользователем {user_id}",
            "metadata": {
                "user_id": user_id
            }
        }, idempotence_key)
        
        # Получаем URL для оплаты
        confirmation_url = payment.confirmation.confirmation_url
        
        # Логируем информацию о созданном платеже
        logger.info(f"Создан платеж для пользователя {user_id}: ID платежа {payment.id}")
        
        return confirmation_url
    except Exception as e:
        logger.error(f"Ошибка при создании платежа: {e}")
        # В случае ошибки возвращаем заглушку
        return f"https://yookassa.ru/checkout/payment?user_id={user_id}" 