#!/bin/bash

set -e

echo "🚀 Начинаем деплой CheckMate Bot..."

# Проверяем, что все необходимые переменные окружения установлены
check_env_vars() {
    local required_vars=("TELEGRAM_BOT_TOKEN" "GEMINI_API_KEY" "OCR_API_KEY")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo "❌ Ошибка: Переменная окружения $var не установлена"
            echo "📝 Проверьте файл .env или установите переменные системы"
            exit 1
        fi
    done
    echo "✅ Все обязательные переменные окружения установлены"
}

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден. Создайте его на основе env.example"
    echo "   cp env.example .env"
    echo "   # Отредактируйте .env с вашими значениями"
    exit 1
fi

# Загружаем переменные из .env
source .env

# Проверяем переменные
check_env_vars

echo "🛠️  Останавливаем старые контейнеры..."
docker-compose down --remove-orphans || true

echo "🏗️  Собираем новый образ..."
docker-compose build --no-cache

echo "📦 Создаем необходимые директории..."
mkdir -p logs

echo "🚀 Запускаем сервис..."
docker-compose up -d

echo "⏳ Ждем запуска сервиса..."
sleep 10

echo "🔍 Проверяем статус контейнера..."
if docker-compose ps | grep -q "Up"; then
    echo "✅ Контейнер запущен успешно"
else
    echo "❌ Ошибка запуска контейнера"
    echo "📋 Логи контейнера:"
    docker-compose logs --tail=20
    exit 1
fi

echo "🔍 Проверяем health check..."
sleep 5
if curl -f http://localhost:8443/health > /dev/null 2>&1; then
    echo "✅ Health check прошел успешно"
else
    echo "⚠️  Health check не прошел, но контейнер запущен"
fi

echo "📊 Информация о запущенном сервисе:"
docker-compose ps

echo "📋 Последние логи:"
docker-compose logs --tail=10

echo ""
echo "🎉 Деплой завершен успешно!"
echo ""
echo "📡 Сервис доступен по адресу: http://localhost:8443"
echo "🏥 Health check: http://localhost:8443/health"
echo "📋 Просмотр логов: docker-compose logs -f"
echo "🛑 Остановка сервиса: docker-compose down"
echo "" 