#!/usr/bin/env python3
"""
Утилита для управления логами CheckMate
- Автоматическая очистка старых логов
- Мониторинг размера логов
- Принудительная ротация логов
"""

import os
import glob
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

class LogCleaner:
    def __init__(self, log_file_path=None, max_size_mb=10):
        # Автоматически определяем путь к лог-файлу
        if log_file_path is None:
            if os.path.exists('checkmate.log') and not os.path.isdir('checkmate.log'):
                log_file_path = 'checkmate.log'
            elif os.path.exists('logs/checkmate.log'):
                log_file_path = 'logs/checkmate.log'
            else:
                # Создаем директорию logs если её нет
                os.makedirs('logs', exist_ok=True)
                log_file_path = 'logs/checkmate.log'
        
        self.log_file_path = log_file_path
        self.max_size_mb = max_size_mb
        self.logger = logging.getLogger(__name__)
    
    def get_log_size_mb(self):
        """Получает размер основного лог-файла в мегабайтах"""
        try:
            if os.path.exists(self.log_file_path):
                size_bytes = os.path.getsize(self.log_file_path)
                size_mb = size_bytes / (1024 * 1024)
                return round(size_mb, 2)
            return 0
        except Exception as e:
            self.logger.error(f"Ошибка при получении размера лога: {e}")
            return 0
    
    def get_log_files(self):
        """Получает список всех файлов логов (включая ротированные)"""
        try:
            log_pattern = f"{self.log_file_path}*"
            log_files = glob.glob(log_pattern)
            return sorted(log_files)
        except Exception as e:
            self.logger.error(f"Ошибка при поиске лог-файлов: {e}")
            return []
    
    def clear_log_completely(self):
        """Полностью очищает основной лог-файл"""
        try:
            if os.path.exists(self.log_file_path):
                # Очищаем файл, но оставляем его существующим
                with open(self.log_file_path, 'w', encoding='utf-8') as f:
                    f.write("")
                self.logger.info(f"Лог-файл {self.log_file_path} полностью очищен")
                return True
            else:
                self.logger.info(f"Лог-файл {self.log_file_path} не существует")
                return True
        except Exception as e:
            self.logger.error(f"Ошибка при очистке лог-файла: {e}")
            return False
    
    def remove_old_rotated_logs(self, days_old=2):
        """Удаляет старые ротированные лог-файлы"""
        try:
            removed_count = 0
            cutoff_time = time.time() - (days_old * 24 * 60 * 60)
            
            # Ищем все файлы, которые начинаются с имени лог-файла
            log_pattern = f"{self.log_file_path}.*"
            old_log_files = glob.glob(log_pattern)
            
            for log_file in old_log_files:
                try:
                    # Проверяем время модификации файла
                    file_mtime = os.path.getmtime(log_file)
                    if file_mtime < cutoff_time:
                        os.remove(log_file)
                        self.logger.info(f"Удален старый лог-файл: {log_file}")
                        removed_count += 1
                except Exception as e:
                    self.logger.error(f"Ошибка при удалении файла {log_file}: {e}")
            
            if removed_count > 0:
                self.logger.info(f"Удалено {removed_count} старых лог-файлов")
            else:
                self.logger.info("Старых лог-файлов для удаления не найдено")
            
            return removed_count
        except Exception as e:
            self.logger.error(f"Ошибка при удалении старых логов: {e}")
            return 0
    
    def check_and_rotate_if_needed(self):
        """Проверяет размер лога и принудительно ротирует при необходимости"""
        try:
            current_size = self.get_log_size_mb()
            
            if current_size > self.max_size_mb:
                self.logger.warning(f"Размер лога {current_size}MB превышает лимит {self.max_size_mb}MB")
                
                # Создаем резервную копию с временной меткой
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{self.log_file_path}.{timestamp}"
                
                try:
                    # Переименовываем текущий лог
                    os.rename(self.log_file_path, backup_name)
                    self.logger.info(f"Лог-файл сохранен как {backup_name}")
                    
                    # Очищаем старые бэкапы
                    self.remove_old_rotated_logs(days_old=2)
                    
                    return True
                except Exception as e:
                    self.logger.error(f"Ошибка при ротации лога: {e}")
                    return False
            else:
                self.logger.info(f"Размер лога {current_size}MB в пределах нормы")
                return True
        except Exception as e:
            self.logger.error(f"Ошибка при проверке размера лога: {e}")
            return False
    
    def get_log_statistics(self):
        """Получает статистику по логам"""
        try:
            stats = {
                'main_log_size_mb': self.get_log_size_mb(),
                'main_log_exists': os.path.exists(self.log_file_path),
                'log_files': self.get_log_files(),
                'total_log_files': 0,
                'total_size_mb': 0
            }
            
            # Подсчитываем общий размер всех лог-файлов
            total_size_bytes = 0
            for log_file in stats['log_files']:
                try:
                    total_size_bytes += os.path.getsize(log_file)
                except:
                    pass
            
            stats['total_log_files'] = len(stats['log_files'])
            stats['total_size_mb'] = round(total_size_bytes / (1024 * 1024), 2)
            
            return stats
        except Exception as e:
            self.logger.error(f"Ошибка при получении статистики логов: {e}")
            return {}

def main():
    """Основная функция для ручного управления логами"""
    print("=== УПРАВЛЕНИЕ ЛОГАМИ CHECKMATE ===")
    print()
    
    cleaner = LogCleaner()
    
    # Получаем статистику
    stats = cleaner.get_log_statistics()
    
    print(f"📊 СТАТИСТИКА ЛОГОВ:")
    print(f"   Основной лог: {stats.get('main_log_size_mb', 0)} MB")
    print(f"   Всего лог-файлов: {stats.get('total_log_files', 0)}")
    print(f"   Общий размер: {stats.get('total_size_mb', 0)} MB")
    print()
    
    print("Выберите действие:")
    print("1. Полностью очистить основной лог")
    print("2. Удалить старые ротированные логи")
    print("3. Проверить и ротировать при необходимости")
    print("4. Показать список всех лог-файлов")
    print("5. Выход")
    
    choice = input("\nВаш выбор (1-5): ").strip()
    
    if choice == "1":
        print("\n🧹 Очистка основного лог-файла...")
        if cleaner.clear_log_completely():
            print("✅ Лог-файл успешно очищен")
        else:
            print("❌ Ошибка при очистке лог-файла")
    
    elif choice == "2":
        print("\n🗑️  Удаление старых ротированных логов...")
        removed = cleaner.remove_old_rotated_logs()
        if removed > 0:
            print(f"✅ Удалено {removed} старых лог-файлов")
        else:
            print("ℹ️  Старых лог-файлов не найдено")
    
    elif choice == "3":
        print("\n🔄 Проверка и ротация логов...")
        if cleaner.check_and_rotate_if_needed():
            print("✅ Проверка завершена успешно")
        else:
            print("❌ Ошибка при проверке/ротации")
    
    elif choice == "4":
        print("\n📋 СПИСОК ВСЕХ ЛОГ-ФАЙЛОВ:")
        log_files = stats.get('log_files', [])
        if log_files:
            for i, log_file in enumerate(log_files, 1):
                try:
                    size_mb = round(os.path.getsize(log_file) / (1024 * 1024), 2)
                    mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                    print(f"   {i}. {log_file} - {size_mb} MB - {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    print(f"   {i}. {log_file} - ошибка получения информации")
        else:
            print("   Лог-файлы не найдены")
    
    elif choice == "5":
        print("👋 До свидания!")
    
    else:
        print("❌ Неверный выбор")

if __name__ == "__main__":
    main() 