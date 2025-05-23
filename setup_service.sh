#!/bin/bash

echo "🔧 Настройка systemd сервиса для CheckMate бота"

# Проверяем права root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите скрипт с правами root: sudo ./setup_service.sh"
    exit 1
fi

# Получаем имя текущего пользователя (не root)
REAL_USER=$(logname 2>/dev/null || echo $SUDO_USER)
CURRENT_DIR=$(pwd)

# Создаем пользователя checkmate если его нет
if ! id "checkmate" &>/dev/null; then
    echo "👤 Создаем пользователя checkmate..."
    useradd -m -s /bin/bash checkmate
fi

# Обновляем пути в service файле
echo "📝 Обновляем пути в service файле..."
sed -i "s|WorkingDirectory=.*|WorkingDirectory=$CURRENT_DIR|g" checkmate-bot.service
sed -i "s|Environment=PATH=.*|Environment=PATH=$CURRENT_DIR/venv/bin|g" checkmate-bot.service
sed -i "s|ExecStart=.*|ExecStart=$CURRENT_DIR/venv/bin/python main.py|g" checkmate-bot.service

# Устанавливаем владельца файлов
echo "🔐 Настраиваем права доступа..."
chown -R checkmate:checkmate $CURRENT_DIR

# Копируем service файл
echo "📋 Устанавливаем systemd сервис..."
cp checkmate-bot.service /etc/systemd/system/

# Перезагружаем systemd и запускаем сервис
systemctl daemon-reload
systemctl enable checkmate-bot
systemctl start checkmate-bot

echo "✅ Сервис установлен и запущен!"
echo ""
echo "Полезные команды:"
echo "  systemctl status checkmate-bot    # Проверить статус"
echo "  systemctl stop checkmate-bot      # Остановить"
echo "  systemctl start checkmate-bot     # Запустить"
echo "  systemctl restart checkmate-bot   # Перезапустить"
echo "  journalctl -u checkmate-bot -f    # Смотреть логи" 