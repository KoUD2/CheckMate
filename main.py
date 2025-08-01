from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters, ConversationHandler
import os
import threading
import asyncio
from telegram.error import Conflict, NetworkError

from config import TELEGRAM_BOT_TOKEN, CHOOSE_TASK, TASK_DESCRIPTION, GRAPH_IMAGE, TASK_SOLUTION, SHOW_ANALYSIS, setup_logging
from handlers.conversation_handlers import (
    start, task_choice, get_task_description, get_graph_image, 
    get_task_solution, show_analysis, cancel, new_task, feedback
)
from handlers.subscription_handlers import subscription_command, promo_command
from handlers.start_handler import start_callback_handler
from handlers.feedback_handlers import rating_feedback
from handlers.admin_handlers import clear_logs_command, log_stats_command, admin_help_command
from webhook_server import run_webhook_server
from services.payment_callbacks import setup_bot
from services.log_cleaner_service import start_log_cleaner

logger = setup_logging()

async def error_handler(update, context):
    """Handle errors caused by updates."""
    error = context.error
    
    if isinstance(error, Conflict):
        logger.warning("Update conflict error: %s", error)
    elif isinstance(error, NetworkError):
        logger.warning("Network error: %s", error)
    else:
        logger.error("Update '%s' caused error: %s", update, error)

def main() -> None:
    """Запуск бота"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("new", new_task)
        ],
        states={
            CHOOSE_TASK: [CallbackQueryHandler(task_choice)],
            TASK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_task_description)],
            GRAPH_IMAGE: [MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, get_graph_image)],
            TASK_SOLUTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_task_solution)],
            SHOW_ANALYSIS: [
                CallbackQueryHandler(show_analysis, pattern="^show_analysis$")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("feedback", feedback),
            CommandHandler("new", new_task)
        ],
    )
    
    application.add_error_handler(error_handler)
    
    application.add_handler(conv_handler)

    application.add_handler(CommandHandler("feedback", feedback))
    application.add_handler(CommandHandler("subscription", subscription_command))
    application.add_handler(CommandHandler("promo", promo_command))
    
    # Административные команды
    application.add_handler(CommandHandler("clear_logs", clear_logs_command))
    application.add_handler(CommandHandler("log_stats", log_stats_command))
    application.add_handler(CommandHandler("admin_help", admin_help_command))
    
    application.add_handler(CallbackQueryHandler(start_callback_handler, pattern="^task_"))

    application.add_handler(CallbackQueryHandler(rating_feedback, pattern="^rating_"))

    webhook_thread = threading.Thread(target=run_webhook_server, daemon=True)
    webhook_thread.start()
    logger.info("Запущен сервер для вебхуков Юкассы")

    # Запускаем сервис автоматической очистки логов в фоновом режиме
    log_cleaner_thread = threading.Thread(
        target=lambda: asyncio.run(start_log_cleaner()), 
        daemon=True
    )
    log_cleaner_thread.start()
    logger.info("Запущен сервис автоматической очистки логов (каждые 2 дня)")

    setup_bot(application.bot)

    logger.info("Запуск бота CheckMate")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
