import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

# Настройка логирования
logger = logging.getLogger(__name__)

async def rating_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопок оценки анализа (лайк/дизлайк)"""
    query = update.callback_query
    await query.answer()
    
    # Получаем тип оценки (like или dislike)
    rating_type = query.data.split("_")[1]
    
    # Определяем текст ответа
    if rating_type == "like":
        feedback_text = "Спасибо за положительную оценку! Пожалуйста, напишите, что именно вам понравилось в анализе."
    else:
        feedback_text = "Спасибо за отзыв! Пожалуйста, напишите, что можно улучшить в анализе."
    
    # Логируем оценку
    logger.info(f"Пользователь {update.effective_user.id} оценил анализ: {rating_type}")
    
    # Удаляем кнопки с текущего сообщения
    await query.edit_message_reply_markup(reply_markup=None)
    
    # Отправляем сообщение с просьбой написать отзыв
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=feedback_text
    ) 