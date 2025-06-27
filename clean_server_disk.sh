#!/bin/bash

echo "🧹 ЭКСТРЕННАЯ ОЧИСТКА СЕРВЕРА"
echo "================================"

# 1. Показать текущее состояние диска
echo "📊 Текущее использование диска:"
df -h

echo ""
echo "🔍 Топ-10 самых больших папок:"
du -sh /* 2>/dev/null | sort -hr | head -10

echo ""
echo "🐳 Docker использование места:"
docker system df

echo ""
echo "================================"
echo "🚨 НАЧИНАЕМ ОЧИСТКУ..."
echo "================================"

# 2. Очистка Docker
echo "🐳 Очищаем Docker мусор..."
docker system prune -af --volumes
docker image prune -af
docker container prune -f
docker volume prune -f

# 3. Очистка логов Docker контейнеров
echo "📝 Очищаем логи Docker контейнеров..."
docker ps -aq | while read container_id; do
    if [ ! -z "$container_id" ]; then
        log_file=$(docker inspect --format='{{.LogPath}}' $container_id 2>/dev/null)
        if [ ! -z "$log_file" ] && [ -f "$log_file" ]; then
            echo "Очищаем лог: $log_file"
            echo "" > "$log_file"
        fi
    fi
done

# 4. Очистка системных логов
echo "🗂️ Очищаем системные логи..."
sudo journalctl --vacuum-time=1d
sudo truncate -s 0 /var/log/*.log 2>/dev/null
sudo truncate -s 0 /var/log/**/*.log 2>/dev/null

# 5. Очистка временных файлов
echo "🗑️ Очищаем временные файлы..."
sudo rm -rf /tmp/*
sudo rm -rf /var/tmp/*
sudo apt-get clean
sudo apt-get autoremove -y

# 6. Поиск больших файлов
echo "🔍 Ищем файлы больше 100MB:"
find / -type f -size +100M -not -path "/proc/*" -not -path "/sys/*" -not -path "/dev/*" 2>/dev/null | head -10

echo ""
echo "================================"
echo "✅ ОЧИСТКА ЗАВЕРШЕНА"
echo "================================"

# 7. Показать результат
echo "📊 Результат очистки:"
df -h

echo ""
echo "🐳 Docker после очистки:"
docker system df

echo ""
echo "🎉 Готово! Если места все еще мало, проверьте большие файлы из списка выше." 