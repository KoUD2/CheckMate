#!/usr/bin/env python3

import os
import sys
import subprocess
from pathlib import Path

def setup_logrotate():
    """Настройка автоматической ротации логов через logrotate"""
    
    # Содержимое конфигурации logrotate
    logrotate_config = """
# CheckMate Bot Logs
/app/logs/checkmate.log /var/log/checkmate*.log {
    daily
    rotate 2
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    maxage 2
    size 50M
    postrotate
        # Перезапуск контейнера для обновления логов (опционально)
        # docker restart checkmate-bot 2>/dev/null || true
    endscript
}

# Docker Container Logs
/var/lib/docker/containers/*/*.log {
    daily
    rotate 1
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    maxage 1
    size 100M
}
"""
    
    try:
        # Создать конфиг файл
        config_path = "/etc/logrotate.d/checkmate-bot"
        
        print("📝 Создаем конфигурацию logrotate...")
        with open("/tmp/checkmate-logrotate", "w") as f:
            f.write(logrotate_config)
        
        # Переместить в системную папку
        subprocess.run(["sudo", "mv", "/tmp/checkmate-logrotate", config_path], check=True)
        subprocess.run(["sudo", "chmod", "644", config_path], check=True)
        
        print(f"✅ Конфигурация создана: {config_path}")
        
        # Тестировать конфигурацию
        print("🧪 Тестируем конфигурацию...")
        result = subprocess.run(["sudo", "logrotate", "-d", config_path], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Конфигурация валидна!")
        else:
            print(f"❌ Ошибка в конфигурации: {result.stderr}")
            return False
        
        # Добавить в crontab для ежедневного запуска
        print("⏰ Настраиваем cron...")
        cron_entry = "0 2 * * * /usr/sbin/logrotate /etc/logrotate.d/checkmate-bot\n"
        
        # Проверить существующий crontab
        result = subprocess.run(["sudo", "crontab", "-l"], 
                              capture_output=True, text=True)
        
        existing_cron = result.stdout if result.returncode == 0 else ""
        
        if "checkmate-bot" not in existing_cron:
            # Добавить новую запись
            new_cron = existing_cron + cron_entry
            
            with open("/tmp/new_crontab", "w") as f:
                f.write(new_cron)
            
            subprocess.run(["sudo", "crontab", "/tmp/new_crontab"], check=True)
            subprocess.run(["rm", "/tmp/new_crontab"], check=True)
            
            print("✅ Cron задача добавлена!")
        else:
            print("✅ Cron задача уже существует!")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка настройки logrotate: {e}")
        return False

def immediate_cleanup():
    """Немедленная очистка текущих логов"""
    print("🧹 Немедленная очистка логов...")
    
    # Очистка логов приложения
    log_files = [
        "/app/logs/checkmate.log",
        "/app/checkmate.log",
        "checkmate.log",
        "logs/checkmate.log"
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            try:
                # Очистить содержимое без удаления файла
                with open(log_file, 'w') as f:
                    f.write("")
                print(f"✅ Очищен: {log_file}")
            except Exception as e:
                print(f"❌ Не удалось очистить {log_file}: {e}")
    
    # Очистка системных логов
    try:
        subprocess.run(["sudo", "journalctl", "--vacuum-time=1d"], check=True)
        print("✅ Системные логи очищены!")
    except:
        print("⚠️ Не удалось очистить системные логи")

if __name__ == "__main__":
    print("🚀 АКТИВАЦИЯ АВТОМАТИЧЕСКОЙ ОЧИСТКИ ЛОГОВ")
    print("=" * 50)
    
    # Немедленная очистка
    immediate_cleanup()
    
    print("\n" + "=" * 50)
    
    # Настройка автоматической ротации
    if setup_logrotate():
        print("\n✅ УСПЕШНО! Автоматическая очистка логов активирована!")
        print("📅 Логи будут автоматически очищаться каждый день в 2:00")
        print("🔄 Максимальный размер лога: 50MB")
        print("📦 Хранение: 2 дня")
    else:
        print("\n❌ Не удалось настроить автоматическую очистку")
        print("💡 Попробуйте запустить скрипт с sudo правами")
    
    print("\n📋 Для ручной очистки используйте:")
    print("   ./emergency_disk_cleanup.sh  - быстрая очистка")
    print("   ./clean_server_disk.sh       - полная очистка") 