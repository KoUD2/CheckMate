#!/usr/bin/env python3
"""
Сервис автоматической очистки логов для CheckMate
Запускается в фоновом режиме и очищает логи каждые 2 дня
"""

import asyncio
import logging
from datetime import datetime, timedelta
from utils.log_cleaner import LogCleaner

class LogCleanerService:
    def __init__(self, cleanup_interval_hours=48):  # 48 часов = 2 дня
        self.cleanup_interval_hours = cleanup_interval_hours
        self.cleanup_interval_seconds = cleanup_interval_hours * 3600
        self.log_cleaner = LogCleaner()
        self.logger = logging.getLogger(__name__)
        self.is_running = False
    
    async def start_background_cleanup(self):
        """Запускает фоновую задачу очистки логов"""
        if self.is_running:
            self.logger.warning("Сервис очистки логов уже запущен")
            return
        
        self.is_running = True
        self.logger.info(f"🧹 Запуск автоматической очистки логов каждые {self.cleanup_interval_hours} часов")
        
        try:
            while self.is_running:
                # Ждем указанный интервал
                await asyncio.sleep(self.cleanup_interval_seconds)
                
                if not self.is_running:
                    break
                
                # Выполняем очистку
                await self.perform_cleanup()
        
        except asyncio.CancelledError:
            self.logger.info("Задача очистки логов отменена")
        except Exception as e:
            self.logger.error(f"Ошибка в сервисе очистки логов: {e}")
        finally:
            self.is_running = False
    
    async def perform_cleanup(self):
        """Выполняет процедуру очистки логов"""
        try:
            self.logger.info("🧹 Начинаем автоматическую очистку логов")
            
            # Получаем статистику до очистки
            stats_before = self.log_cleaner.get_log_statistics()
            size_before = stats_before.get('total_size_mb', 0)
            files_before = stats_before.get('total_log_files', 0)
            
            self.logger.info(f"📊 До очистки: {files_before} файлов, {size_before} MB")
            
            # Удаляем старые ротированные логи
            removed_files = self.log_cleaner.remove_old_rotated_logs(days_old=2)
            
            # Проверяем размер основного лога и ротируем при необходимости
            self.log_cleaner.check_and_rotate_if_needed()
            
            # Получаем статистику после очистки
            stats_after = self.log_cleaner.get_log_statistics()
            size_after = stats_after.get('total_size_mb', 0)
            files_after = stats_after.get('total_log_files', 0)
            
            freed_space = size_before - size_after
            
            self.logger.info(f"📊 После очистки: {files_after} файлов, {size_after} MB")
            if freed_space > 0:
                self.logger.info(f"💾 Освобождено места: {freed_space:.2f} MB")
            
            self.logger.info("✅ Автоматическая очистка логов завершена")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка при автоматической очистке логов: {e}")
    
    def stop(self):
        """Останавливает сервис очистки логов"""
        if self.is_running:
            self.logger.info("🛑 Остановка сервиса очистки логов")
            self.is_running = False
        else:
            self.logger.info("Сервис очистки логов уже остановлен")
    
    async def cleanup_now(self):
        """Выполняет немедленную очистку логов"""
        self.logger.info("🧹 Принудительная очистка логов")
        await self.perform_cleanup()

# Глобальный экземпляр сервиса
_log_cleaner_service = None

def get_log_cleaner_service():
    """Получает глобальный экземпляр сервиса очистки логов"""
    global _log_cleaner_service
    if _log_cleaner_service is None:
        _log_cleaner_service = LogCleanerService()
    return _log_cleaner_service

async def start_log_cleaner():
    """Запускает сервис очистки логов"""
    service = get_log_cleaner_service()
    await service.start_background_cleanup()

def stop_log_cleaner():
    """Останавливает сервис очистки логов"""
    service = get_log_cleaner_service()
    service.stop()

async def cleanup_logs_now():
    """Выполняет немедленную очистку логов"""
    service = get_log_cleaner_service()
    await service.cleanup_now() 