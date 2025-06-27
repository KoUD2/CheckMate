#!/bin/bash

echo "🔧 Исправление проблемы с логами CheckMate"
echo "=========================================="

# Останавливаем контейнер
echo "🛑 Останавливаем контейнер..."
docker compose down

# Проверяем наличие проблемной директории
if [ -d "./checkmate.log" ]; then
    echo "⚠️  Обнаружена директория checkmate.log"
    echo "🗑️  Удаляем директорию..."
    rm -rf ./checkmate.log
    echo "✅ Директория удалена"
else
    echo "ℹ️  Директория checkmate.log не найдена"
fi

# Создаем директорию для логов если её нет
if [ ! -d "./logs" ]; then
    echo "📁 Создаем директорию logs..."
    mkdir -p ./logs
    echo "✅ Директория logs создана"
fi

# Устанавливаем правильные права доступа
echo "🔐 Устанавливаем права доступа..."
chmod 755 ./logs

echo "🚀 Запускаем контейнер..."
docker compose up -d

echo "📋 Проверяем статус..."
sleep 5
docker compose ps

echo ""
echo "✅ Готово! Проблема с логами исправлена"
echo "📝 Логи теперь сохраняются в директории ./logs/"
echo ""
echo "🔍 Для проверки используйте:"
echo "   docker compose logs -f checkmate-bot" 