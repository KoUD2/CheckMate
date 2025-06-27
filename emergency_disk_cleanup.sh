#!/bin/bash

echo "🚨 ЭКСТРЕННАЯ ОЧИСТКА ДИСКА - БЫСТРЫЙ РЕЖИМ"
echo "============================================"

# Показать текущее состояние
echo "Текущее состояние диска:"
df -h /

echo ""
echo "🚨 КРИТИЧЕСКАЯ ОЧИСТКА..."

# 1. Очистка Docker (самое эффективное)
echo "🐳 Очищаем Docker..."
docker system prune -af --volumes 2>/dev/null
docker image prune -af 2>/dev/null

# 2. Очистка логов Docker контейнеров
echo "📝 Очищаем логи контейнеров..."
for container in $(docker ps -aq 2>/dev/null); do
    log_file=$(docker inspect --format='{{.LogPath}}' $container 2>/dev/null)
    if [ -f "$log_file" ]; then
        echo "" > "$log_file"
    fi
done

# 3. Очистка системных логов
echo "🗂️ Очищаем системные логи..."
sudo journalctl --vacuum-time=1h 2>/dev/null
sudo truncate -s 0 /var/log/*.log 2>/dev/null

# 4. Очистка APT кэша
echo "📦 Очищаем APT кэш..."
sudo apt-get clean 2>/dev/null
sudo apt-get autoremove -y 2>/dev/null

# 5. Очистка временных файлов
echo "🗑️ Очищаем /tmp..."
sudo rm -rf /tmp/* 2>/dev/null

echo ""
echo "✅ ЭКСТРЕННАЯ ОЧИСТКА ЗАВЕРШЕНА!"
echo "Результат:"
df -h /

echo ""
echo "📋 Если места все еще мало, запустите: ./clean_server_disk.sh" 