#!/usr/bin/env python3
"""
Экстренное исправление проблемы с логами CheckMate
Этот скрипт может быть запущен прямо на сервере для быстрого исправления
"""

import os
import shutil
import subprocess
import sys

def fix_log_issue():
    """Исправляет проблему с директорией checkmate.log"""
    print("🔧 ЭКСТРЕННОЕ ИСПРАВЛЕНИЕ ЛОГОВ CHECKMATE")
    print("=" * 50)
    
    try:
        # 1. Останавливаем контейнер
        print("🛑 Останавливаем контейнер...")
        result = subprocess.run(['docker', 'compose', 'down'], 
                              capture_output=True, text=True, cwd='.')
        if result.returncode == 0:
            print("✅ Контейнер остановлен")
        else:
            print(f"⚠️ Ошибка при остановке контейнера: {result.stderr}")
        
        # 2. Проверяем и удаляем проблемную директорию
        if os.path.exists('./checkmate.log') and os.path.isdir('./checkmate.log'):
            print("⚠️ Обнаружена директория checkmate.log")
            print("🗑️ Удаляем директорию...")
            shutil.rmtree('./checkmate.log')
            print("✅ Директория удалена")
        else:
            print("ℹ️ Директория checkmate.log не найдена")
        
        # 3. Создаем директорию для логов
        if not os.path.exists('./logs'):
            print("📁 Создаем директорию logs...")
            os.makedirs('./logs', exist_ok=True)
            print("✅ Директория logs создана")
        
        # 4. Устанавливаем права доступа
        print("🔐 Устанавливаем права доступа...")
        os.chmod('./logs', 0o755)
        print("✅ Права доступа установлены")
        
        # 5. Запускаем контейнер
        print("🚀 Запускаем контейнер...")
        result = subprocess.run(['docker', 'compose', 'up', '-d'], 
                              capture_output=True, text=True, cwd='.')
        if result.returncode == 0:
            print("✅ Контейнер запущен")
        else:
            print(f"❌ Ошибка при запуске контейнера: {result.stderr}")
            return False
        
        # 6. Проверяем статус
        print("📋 Проверяем статус...")
        import time
        time.sleep(5)
        
        result = subprocess.run(['docker', 'compose', 'ps'], 
                              capture_output=True, text=True, cwd='.')
        if result.returncode == 0:
            print("Статус контейнеров:")
            print(result.stdout)
        
        print("\n✅ ПРОБЛЕМА ИСПРАВЛЕНА!")
        print("📝 Логи теперь сохраняются в директории ./logs/")
        print("\n🔍 Для проверки используйте:")
        print("   docker compose logs -f checkmate-bot")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при исправлении: {e}")
        return False

def show_current_status():
    """Показывает текущий статус логов"""
    print("\n📊 ТЕКУЩИЙ СТАТУС ЛОГОВ:")
    print("-" * 30)
    
    # Проверяем checkmate.log
    if os.path.exists('./checkmate.log'):
        if os.path.isdir('./checkmate.log'):
            print("❌ checkmate.log - ДИРЕКТОРИЯ (проблема!)")
        else:
            size = os.path.getsize('./checkmate.log') / (1024*1024)
            print(f"✅ checkmate.log - файл ({size:.2f} MB)")
    else:
        print("ℹ️ checkmate.log - не существует")
    
    # Проверяем logs директорию
    if os.path.exists('./logs'):
        if os.path.isdir('./logs'):
            files = os.listdir('./logs')
            print(f"📁 logs/ - директория ({len(files)} файлов)")
            for file in files[:5]:  # Показываем первые 5 файлов
                path = os.path.join('./logs', file)
                if os.path.isfile(path):
                    size = os.path.getsize(path) / (1024*1024)
                    print(f"   📄 {file} ({size:.2f} MB)")
        else:
            print("❌ logs - файл (должна быть директория!)")
    else:
        print("ℹ️ logs/ - не существует")

def main():
    """Основная функция"""
    print("ЭКСТРЕННОЕ ИСПРАВЛЕНИЕ ЛОГОВ CHECKMATE")
    print("====================================")
    
    # Показываем текущий статус
    show_current_status()
    
    # Спрашиваем, нужно ли исправлять
    if os.path.exists('./checkmate.log') and os.path.isdir('./checkmate.log'):
        print("\n⚠️ ОБНАРУЖЕНА ПРОБЛЕМА: checkmate.log является директорией!")
        response = input("Исправить проблему? (y/N): ").strip().lower()
        
        if response in ['y', 'yes', 'да']:
            success = fix_log_issue()
            if success:
                print("\n🎉 Проблема успешно исправлена!")
            else:
                print("\n❌ Не удалось исправить проблему")
                sys.exit(1)
        else:
            print("Отмена исправления")
    else:
        print("\n✅ Проблем с логами не обнаружено")

if __name__ == "__main__":
    main() 