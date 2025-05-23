import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from config import CHOOSE_TASK
from services.api_service import register_user

# Настройка логирования
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Глобальный обработчик команды /start, работает вне ConversationHandler"""
    # Получаем информацию о пользователе
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    logger.info(f"Пользователь {user_id} (@{username}) запустил команду /start")
    
    # Регистрируем пользователя в системе
    registration_success = await register_user(user_id, username)
    
    if registration_success:
        logger.info(f"Пользователь {user_id} успешно зарегистрирован/уже был зарегистрирован")
    else:
        logger.warning(f"Не удалось зарегистрировать пользователя {user_id}")
    
    # Создаем клавиатуру с кнопками
    keyboard = [
        [InlineKeyboardButton("Задание 37", callback_data="task_37")],
        [InlineKeyboardButton("Задание 38", callback_data="task_38")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем приветственное сообщение с меню
    await update.message.reply_text(
        "👋 Привет! Я бот CheckMate, который поможет проверить твое решение заданий ЕГЭ по ангдийскому.\n\n"
        "Выбери задание:",
        reply_markup=reply_markup
    )

async def start_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопок из меню /start"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("task_"):
        task_number = query.data.split("_")[1]
        await query.message.reply_text(
            f"Чтобы начать проверку задания {task_number}, отправьте команду /new"
        ) 