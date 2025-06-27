#!/usr/bin/env python3
"""
Обработчики административных команд для CheckMate
"""

from telegram import Update
from telegram.ext import ContextTypes
import logging
from services.log_cleaner_service import cleanup_logs_now, get_log_cleaner_service

# Настройка логирования
logger = logging.getLogger(__name__)

ADMIN_IDS = {
    1054927360,
}

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

async def clear_logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /clear_logs для очистки логов"""
    user_id = update.effective_user.id
    
    # Проверяем права администратора
    if not is_admin(user_id):
        await update.message.reply_text(
            "❌ У вас нет прав для выполнения этой команды."
        )
        return
    
    try:
        # Получаем статистику до очистки
        service = get_log_cleaner_service()
        stats_before = service.log_cleaner.get_log_statistics()
        size_before = stats_before.get('total_size_mb', 0)
        files_before = stats_before.get('total_log_files', 0)
        
        await update.message.reply_text(
            f"🧹 Начинаем очистку логов...\n\n"
            f"📊 До очистки:\n"
            f"   • Файлов: {files_before}\n"
            f"   • Размер: {size_before} MB"
        )
        
        # Выполняем очистку
        await cleanup_logs_now()
        
        # Получаем статистику после очистки
        stats_after = service.log_cleaner.get_log_statistics()
        size_after = stats_after.get('total_size_mb', 0)
        files_after = stats_after.get('total_log_files', 0)
        
        freed_space = size_before - size_after
        
        await update.message.reply_text(
            f"✅ Очистка логов завершена!\n\n"
            f"📊 После очистки:\n"
            f"   • Файлов: {files_after}\n"
            f"   • Размер: {size_after} MB\n"
            f"   • Освобождено: {freed_space:.2f} MB"
        )
        
        logger.info(f"Администратор {user_id} выполнил ручную очистку логов")
        
    except Exception as e:
        logger.error(f"Ошибка при ручной очистке логов: {e}")
        await update.message.reply_text(
            f"❌ Ошибка при очистке логов: {str(e)}"
        )

async def log_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /log_stats для получения статистики логов"""
    user_id = update.effective_user.id
    
    # Проверяем права администратора
    if not is_admin(user_id):
        await update.message.reply_text(
            "❌ У вас нет прав для выполнения этой команды."
        )
        return
    
    try:
        service = get_log_cleaner_service()
        stats = service.log_cleaner.get_log_statistics()
        
        main_size = stats.get('main_log_size_mb', 0)
        total_files = stats.get('total_log_files', 0)
        total_size = stats.get('total_size_mb', 0)
        log_files = stats.get('log_files', [])
        
        message = f"📊 СТАТИСТИКА ЛОГОВ\n\n"
        message += f"📄 Основной лог: {main_size} MB\n"
        message += f"📁 Всего файлов: {total_files}\n"
        message += f"💾 Общий размер: {total_size} MB\n\n"
        
        if log_files:
            message += "📋 Список файлов:\n"
            for i, log_file in enumerate(log_files[:10], 1):  # Показываем только первые 10
                try:
                    import os
                    size_mb = round(os.path.getsize(log_file) / (1024 * 1024), 2)
                    filename = os.path.basename(log_file)
                    message += f"   {i}. {filename} - {size_mb} MB\n"
                except:
                    message += f"   {i}. {log_file} - ошибка\n"
            
            if len(log_files) > 10:
                message += f"   ... и еще {len(log_files) - 10} файлов\n"
        else:
            message += "📋 Лог-файлы не найдены"
        
        await update.message.reply_text(message)
        
        logger.info(f"Администратор {user_id} запросил статистику логов")
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики логов: {e}")
        await update.message.reply_text(
            f"❌ Ошибка при получении статистики: {str(e)}"
        )

async def admin_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /admin_help для показа административных команд"""
    user_id = update.effective_user.id
    
    # Проверяем права администратора
    if not is_admin(user_id):
        await update.message.reply_text(
            "❌ У вас нет прав для выполнения этой команды."
        )
        return
    
    help_text = """
🔧 АДМИНИСТРАТИВНЫЕ КОМАНДЫ

📊 /log_stats - Статистика логов
🧹 /clear_logs - Очистка логов
❓ /admin_help - Эта справка

ℹ️ Автоматическая очистка логов происходит каждые 2 дня.
    """
    
    await update.message.reply_text(help_text)
    logger.info(f"Администратор {user_id} запросил справку по административным командам") 