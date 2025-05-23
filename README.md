# CheckMate Telegram Bot

Телеграм бот для проверки заданий ЕГЭ 37 и 38 с использованием ИИ.

## Функции

- Проверка задания 37 (личное письмо)
- Проверка задания 38 (описание графика)
- 📊 OCR распознавание графиков
- 💳 Система подписок через ЮKassa
- 🔄 API интеграция с checkmateai.ru

## Требования

- Python 3.8+
- Ubuntu/Debian сервер
- Systemd для автозапуска

## Быстрый деплой на Timeweb

### 1. Подключение к серверу

```bash
ssh root@your-server-ip
```

### 2. Установка зависимостей

```bash
# Обновляем систему
apt update && apt upgrade -y

# Устанавливаем Python и необходимые пакеты
apt install -y python3 python3-pip python3-venv git nano

# Устанавливаем Python dotenv для работы с .env файлами
pip3 install python-dotenv
```

### 3. Клонирование проекта

```bash
# Переходим в домашнюю директорию
cd /home

# Клонируем репозиторий (замените на ваш URL)
git clone https://github.com/yourusername/CheckMate.git
cd CheckMate

# Делаем скрипты исполняемыми
chmod +x deploy.sh setup_service.sh
```

### 4. Запуск деплоя

```bash
# Запускаем автоматический деплой
./deploy.sh
```

### 5. Настройка переменных окружения

```bash
# Редактируем .env файл
nano .env
```

Заполните все необходимые переменные:

```env
TELEGRAM_BOT_TOKEN=ваш_токен_бота
GEMINI_API_KEY=ваш_ключ_gemini
OCR_API_KEY=ваш_ключ_ocr
YOOKASSA_SHOP_ID=ваш_id_магазина
YOOKASSA_SECRET_KEY=ваш_секретный_ключ
WEBHOOK_URL=https://ваш-домен.com/payment-webhook
```

### 6. Установка и запуск сервиса

```bash
# Устанавливаем systemd сервис
sudo ./setup_service.sh
```

## Управление ботом

### Основные команды

```bash
# Проверить статус
systemctl status checkmate-bot

# Остановить бота
sudo systemctl stop checkmate-bot

# Запустить бота
sudo systemctl start checkmate-bot

# Перезапустить бота
sudo systemctl restart checkmate-bot

# Смотреть логи в реальном времени
journalctl -u checkmate-bot -f

# Смотреть последние логи
journalctl -u checkmate-bot -n 100
```

### Обновление кода

```bash
cd /home/CheckMate

# Останавливаем бота
sudo systemctl stop checkmate-bot

# Обновляем код
git pull

# Запускаем бота
sudo systemctl start checkmate-bot
```

## Настройка домена и SSL

### 1. Настройка Nginx (опционально)

```bash
# Устанавливаем Nginx
apt install -y nginx

# Создаем конфиг для домена
nano /etc/nginx/sites-available/checkmate
```

Конфиг Nginx:

```nginx
server {
    listen 80;
    server_name ваш-домен.com;

    location /payment-webhook {
        proxy_pass http://localhost:8443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Активируем сайт
ln -s /etc/nginx/sites-available/checkmate /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### 2. SSL сертификат

```bash
# Устанавливаем Certbot
apt install -y certbot python3-certbot-nginx

# Получаем SSL сертификат
certbot --nginx -d ваш-домен.com
```

## Мониторинг

### Логи

```bash
# Логи бота
journalctl -u checkmate-bot

# Логи в файле
tail -f /home/CheckMate/checkmate.log
```

### Автоматический мониторинг

Создайте cron задачу для проверки работы бота:

```bash
crontab -e

# Добавьте строку (проверка каждые 5 минут)
*/5 * * * * systemctl is-active --quiet checkmate-bot || systemctl restart checkmate-bot
```

## Структура проекта

```
CheckMate/
├── main.py                    # Главный файл запуска
├── config.py                  # Конфигурация
├── requirements.txt           # Зависимости Python
├── deploy.sh                  # Скрипт деплоя
├── setup_service.sh           # Установка systemd сервиса
├── checkmate-bot.service      # Systemd unit файл
├── env.example                # Пример переменных окружения
├── handlers/                  # Обработчики Telegram
├── services/                  # Сервисы (API, OCR, AI)
└── prompts/                   # Промпты для ИИ
```

## Поддержка

Если возникли проблемы:

1. Проверьте логи: `journalctl -u checkmate-bot -f`
2. Проверьте статус: `systemctl status checkmate-bot`
3. Проверьте .env файл на корректность
4. Перезапустите бота: `sudo systemctl restart checkmate-bot`

## API Endpoints

Бот интегрируется с API:

- `GET /tgusers/{tg_id}` - получение данных пользователя
- `POST /tgusers` - регистрация нового пользователя
- `PATCH /tgusers/{tg_id}/subscription` - обновление подписки
- `PATCH /tgusers/{tg_id}/free_checks` - изменение счетчика проверок
