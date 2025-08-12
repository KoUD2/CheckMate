from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging
from datetime import datetime, timedelta
import re
import json
import os

from services.payment_service import create_payment_link
from services.api_service import get_user_subscription, calculate_days_left, update_user_subscription
from services.payment_callbacks import get_all_active_subscriptions, activate_subscription

# Настройка логирования
logger = logging.getLogger(__name__)

# Файл для сохранения промокодов
PROMO_CODES_FILE = "promo_codes.json"

# Система промокодов
PROMO_CODES = {
    "TEACHY": {
        "days": 30,
        "end_date": datetime(2025, 8, 9, 23, 59, 59),
        "description": "Промокод для учителей"
    },
    "NATALYAPRO": {
        "days": 30,
        "end_date": datetime(2025, 12, 31, 23, 59, 59),
        "description": "Одноразовый промокод NatalyaPRO"
    }
}

# Хранилище использованных промокодов (в реальном проекте должно быть в БД)
USED_PROMO_CODES = set()

def load_promo_codes():
    """Загружает промокоды из файла"""
    global PROMO_CODES
    if os.path.exists(PROMO_CODES_FILE):
        try:
            with open(PROMO_CODES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Преобразуем строки дат обратно в datetime объекты
                for code, info in data.items():
                    if isinstance(info['end_date'], str):
                        info['end_date'] = datetime.fromisoformat(info['end_date'])
                PROMO_CODES.update(data)
                logger.info(f"Загружено {len(data)} промокодов из файла")
        except Exception as e:
            logger.error(f"Ошибка при загрузке промокодов: {e}")

def save_promo_codes():
    """Сохраняет промокоды в файл"""
    try:
        # Преобразуем datetime объекты в строки для JSON
        data_to_save = {}
        for code, info in PROMO_CODES.items():
            data_to_save[code] = {
                'days': info['days'],
                'end_date': info['end_date'].isoformat(),
                'description': info['description']
            }
        
        with open(PROMO_CODES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        logger.info(f"Сохранено {len(PROMO_CODES)} промокодов в файл")
    except Exception as e:
        logger.error(f"Ошибка при сохранении промокодов: {e}")

def is_promo_code_used(user_id: int, promo_code: str) -> bool:
    """Проверяет, использовал ли пользователь промокод"""
    return f"{user_id}_{promo_code}" in USED_PROMO_CODES

def mark_promo_code_as_used(user_id: int, promo_code: str) -> None:
    """Отмечает промокод как использованный"""
    USED_PROMO_CODES.add(f"{user_id}_{promo_code}")
    logger.info(f"Промокод {promo_code} отмечен как использованный для пользователя {user_id}")

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
    
    # Проверяем, что промокод существует
    if promo_code not in PROMO_CODES:
        await update.message.reply_text(
            "❌ Неверный промокод.\n\n"
            "Пожалуйста, проверьте правильность введенного кода."
        )
        return
    
    promo_info = PROMO_CODES[promo_code]
    
    # Проверяем, не истек ли срок действия промокода
    if datetime.now() > promo_info["end_date"]:
        await update.message.reply_text(
            f"❌ Срок действия промокода истек.\n\n"
            f"Промокод действовал до {promo_info['end_date'].strftime('%d.%m.%Y')}."
        )
        return
    
    # Проверяем, не использовал ли пользователь этот промокод ранее
    if is_promo_code_used(user_id, promo_code):
        await update.message.reply_text(
            "❌ Вы уже использовали этот промокод.\n\n"
            "Каждый промокод можно использовать только один раз."
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
    logger.info(f"Активируем подписку по промокоду {promo_code} для пользователя {user_id}")
    api_success = await update_user_subscription(user_id, promo_info["days"])
    
    # Активируем подписку локально (всегда, независимо от результата API)
    activate_subscription(user_id, promo_info["days"])
    
    # Отмечаем промокод как использованный
    mark_promo_code_as_used(user_id, promo_code)
    
    # Получаем информацию о подписке для уведомления
    subscription = get_all_active_subscriptions().get(user_id)
    expiry_date_str = subscription["expiry_date"].strftime("%d.%m.%Y")
    days_left = (subscription["expiry_date"] - datetime.now()).days
    
    # Формируем сообщение в зависимости от результата API
    if api_success:
        message = f"✅ Промокод {promo_code} успешно активирован!\n\n"
    else:
        message = f"✅ Промокод {promo_code} активирован локально!\n\n"
        message += "⚠️ Примечание: Подписка активирована локально. API недоступен.\n\n"
    
    message += f"Ваша подписка активирована до {expiry_date_str}.\n"
    message += f"Осталось дней: {days_left}.\n\n"
    message += f"Спасибо за использование CheckMate!"
    
    # Отправляем уведомление об успешной активации
    await update.message.reply_text(message)
    
    logger.info(f"Промокод {promo_code} успешно активирован для пользователя {user_id}")

async def add_promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /addpromo для создания нового промокода"""
    user_id = update.effective_user.id
    
    # Проверяем права администратора (используем тот же список, что и в admin_handlers.py)
    ADMIN_IDS = {1054927360}
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(
            "❌ У вас нет прав для выполнения этой команды."
        )
        return
    
    # Проверяем, передан ли промокод
    if not context.args:
        await update.message.reply_text(
            "❌ Пожалуйста, укажите название промокода.\n\n"
            "Использование: /addpromo <НАЗВАНИЕ_ПРОМОКОДА>"
        )
        return
    
    promo_code = context.args[0].upper()
    
    # Проверяем, что промокод не содержит недопустимых символов
    if not re.match(r'^[A-Z0-9]+$', promo_code):
        await update.message.reply_text(
            "❌ Название промокода может содержать только буквы и цифры."
        )
        return
    
    # Проверяем, что промокод не существует
    if promo_code in PROMO_CODES:
        await update.message.reply_text(
            f"❌ Промокод {promo_code} уже существует."
        )
        return
    
    # Создаем новый промокод на месяц (30 дней)
    new_promo = {
        "days": 30,
        "end_date": datetime.now() + timedelta(days=365),  # Действует год
        "description": f"Одноразовый промокод {promo_code}"
    }
    
    # Добавляем промокод в систему
    PROMO_CODES[promo_code] = new_promo
    
    # Сохраняем в файл
    save_promo_codes()
    
    # Отправляем подтверждение
    await update.message.reply_text(
        f"✅ Промокод {promo_code} успешно создан!\n\n"
        f"📋 Информация:\n"
        f"   • Период: 30 дней\n"
        f"   • Действует до: {new_promo['end_date'].strftime('%d.%m.%Y')}\n"
        f"   • Тип: Одноразовый\n"
        f"   • Описание: {new_promo['description']}\n\n"
        f"🎫 Пользователи могут активировать его командой:\n"
        f"   /promo {promo_code}"
    )
    
    logger.info(f"Администратор {user_id} создал новый промокод: {promo_code}")

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

# Загружаем промокоды при импорте модуля
load_promo_codes() 