from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging
from datetime import datetime, timedelta
import re

from services.payment_service import create_payment_link
from services.api_service import get_user_subscription, calculate_days_left, update_user_subscription
from services.payment_callbacks import get_all_active_subscriptions, activate_subscription

# Настройка логирования
logger = logging.getLogger(__name__)

# Промокод и дата окончания действия
PROMO_CODE = "TEACHY"
PROMO_END_DATE = datetime(2025, 8, 9, 23, 59, 59)

async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /promo для активации промокода"""
    user_id = update.effective_user.id
    
    # Проверяем, передан ли промокод
    if not context.args:
        await update.message.reply_text(
            "❌ Пожалуйста, укажите промокод.\n\n"
            "Использование: /promo <код>"
        )
        return
    
    promo_code = context.args[0].upper()
    
    # Проверяем, что промокод правильный
    if promo_code != PROMO_CODE:
        await update.message.reply_text(
            "❌ Неверный промокод.\n\n"
            "Пожалуйста, проверьте правильность введенного кода."
        )
        return
    
    # Проверяем, не истек ли срок действия промокода
    if datetime.now() > PROMO_END_DATE:
        await update.message.reply_text(
            "❌ Срок действия промокода истек.\n\n"
            "Промокод действовал до 9 августа 2025 года."
        )
        return
    
    # Проверяем, есть ли у пользователя активная подписка
    local_subscriptions = get_all_active_subscriptions()
    local_subscription = local_subscriptions.get(user_id)
    
    has_active_subscription = False
    
    # Проверяем локальную подписку
    if local_subscription and local_subscription.get("is_active"):
        expiry_date = local_subscription.get("expiry_date")
        if expiry_date and expiry_date > datetime.now():
            has_active_subscription = True
            logger.info(f"Пользователь {user_id} имеет активную локальную подписку")
    
    # Проверяем API подписку
    if not has_active_subscription:
        user_data = await get_user_subscription(user_id)
        if user_data and user_data.get("IsActive", False):
            has_active_subscription = True
            logger.info(f"Пользователь {user_id} имеет активную API подписку")
    
    if has_active_subscription:
        await update.message.reply_text(
            "❌ Промокод не может быть использован.\n\n"
            "У вас уже есть активная подписка. Промокод можно использовать только один раз."
        )
        return
    
    # Активируем подписку через API
    logger.info(f"Активируем подписку по промокоду для пользователя {user_id}")
    api_success = await update_user_subscription(user_id, 30)
    
    if not api_success:
        logger.error(f"Не удалось активировать подписку через API для пользователя {user_id}")
        await update.message.reply_text(
            "❌ Произошла ошибка при активации промокода.\n\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку."
        )
        return
    
    # Активируем подписку локально
    activate_subscription(user_id, 30)
    
    # Получаем информацию о подписке для уведомления
    subscription = get_all_active_subscriptions().get(user_id)
    expiry_date_str = subscription["expiry_date"].strftime("%d.%m.%Y")
    days_left = (subscription["expiry_date"] - datetime.now()).days
    
    # Отправляем уведомление об успешной активации
    await update.message.reply_text(
        f"✅ Промокод успешно активирован!\n\n"
        f"Ваша подписка активирована до {expiry_date_str}.\n"
        f"Осталось дней: {days_left}.\n\n"
        f"Спасибо за использование CheckMate!"
    )
    
    logger.info(f"Промокод успешно активирован для пользователя {user_id}")

async def subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /subscription"""
    user_id = update.effective_user.id
    
    # Проверяем сначала локальное хранилище (активные платежи)
    local_subscriptions = get_all_active_subscriptions()
    local_subscription = local_subscriptions.get(user_id)
    
    is_active = False
    days_left = 0
    
    if local_subscription and local_subscription.get("is_active"):
        # Проверяем не истекла ли локальная подписка
        expiry_date = local_subscription.get("expiry_date")
        if expiry_date and expiry_date > datetime.now():
            is_active = True
            days_left = (expiry_date - datetime.now()).days
            logger.info(f"Найдена активная локальная подписка для пользователя {user_id}, дней осталось: {days_left}")
    
    # Если локальной подписки нет, проверяем API (для обратной совместимости)
    if not is_active:
        user_data = await get_user_subscription(user_id)
        
        if user_data and user_data.get("IsActive", False):
            # Подписка активна в API
            is_active = True
            
            # Получаем дату окончания подписки и вычисляем оставшиеся дни
            sub_until = user_data.get("SubUntil", "")
            if sub_until:
                days_left = calculate_days_left(sub_until)
            logger.info(f"Найдена активная API подписка для пользователя {user_id}, дней осталось: {days_left}")
    
    # Формируем сообщение
    if is_active:
        if days_left == 1:
            message_text = f"✅ Ваша подписка активна.\nОстался 1 день."
        elif days_left < 5:
            message_text = f"✅ Ваша подписка активна.\nОсталось {days_left} дня."
        else:
            message_text = f"✅ Ваша подписка активна.\nОсталось {days_left} дней."
    else:
        # Подписка не активна
        message_text = "❌ Ваша подписка истекла"
    
    # Добавляем информацию о стоимости подписки
    message_text += "\n\nСтоимость подписки: 149 руб./месяц"
    
    # Создаем кнопку для оплаты, только если подписка не активна
    try:
        if not is_active:
            payment_url = await create_payment_link(user_id)
            
            # Логируем успешное создание ссылки на оплату
            logger.info(f"Создана ссылка на оплату для пользователя {user_id}: {payment_url}")
            
            keyboard = [
                [InlineKeyboardButton("Оплатить подписку", url=payment_url)]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем сообщение с кнопкой оплаты
            await update.message.reply_text(
                message_text,
                reply_markup=reply_markup
            )
        else:
            # Для активной подписки отправляем сообщение без кнопки оплаты
            await update.message.reply_text(message_text)
    except Exception as e:
        logger.error(f"Ошибка при создании платежа для пользователя {user_id}: {e}")
        # В случае ошибки отправляем сообщение без кнопки
        await update.message.reply_text(
            message_text + "\n\nИзвините, в данный момент оплата недоступна. Попробуйте позже."
        )

# В реальном проекте здесь должны быть хэндлеры для обработки вебхуков от Юкассы
# Например:
# async def process_payment_notification(payment_data):
#     """Обработка уведомления о платеже от Юкассы"""
#     payment_id = payment_data.get('object', {}).get('id')
#     status = payment_data.get('object', {}).get('status')
#     metadata = payment_data.get('object', {}).get('metadata', {})
#     user_id = metadata.get('user_id')
#     
#     if status == 'succeeded':
#         # Успешный платеж, активируем подписку
#         # Здесь должен быть код для работы с БД
#         logger.info(f"Успешная оплата: {payment_id} для пользователя {user_id}")
#     else:
#         logger.warning(f"Платеж не подтвержден: {payment_id}, статус: {status}") 