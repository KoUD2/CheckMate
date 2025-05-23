# 🚀 Пошаговый гайд деплоя на Timeweb

## Подготовка файлов на локальном компьютере

1. **Упакуйте проект в архив** (исключая логи и кэш):
   ```
   Создайте ZIP архив со всеми файлами проекта, кроме:
   - checkmate.log
   - __pycache__/
   - .env (создадите на сервере)
   ```

## Деплой на сервер Timeweb

### 1. Подключение к серверу

```bash
ssh root@ваш-ip-адрес-сервера
```

### 2. Установка системных зависимостей

```bash
# Обновляем систему
apt update && apt upgrade -y

# Устанавливаем необходимые пакеты
apt install -y python3 python3-pip python3-venv git nano unzip wget curl

# Проверяем версию Python (должна быть 3.8+)
python3 --version
```

### 3. Загрузка проекта на сервер

**Вариант A: Через Git (рекомендуется)**

```bash
cd /home
git clone https://github.com/ваш-репозиторий/CheckMate.git
cd CheckMate
```

**Вариант B: Через SCP/SFTP**

```bash
# На вашем локальном компьютере:
scp checkmate.zip root@ваш-ip:/home/

# На сервере:
cd /home
unzip checkmate.zip
cd CheckMate
```

### 4. Автоматический деплой

```bash
# Делаем скрипты исполняемыми
chmod +x deploy.sh setup_service.sh

# Запускаем автоматическую установку
./deploy.sh
```

### 5. Настройка переменных окружения

```bash
# Редактируем файл с переменными окружения
nano .env
```

**Заполните следующие данные:**

```env
# Токен вашего Telegram бота
TELEGRAM_BOT_TOKEN=1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA

# API ключ Google Gemini
GEMINI_API_KEY=AIzaSyA...

# API ключ OCR.space
OCR_API_KEY=K123...

# Данные ЮKassa
YOOKASSA_SHOP_ID=123456
YOOKASSA_SECRET_KEY=live_...

# Webhook для платежей (ваш домен)
WEBHOOK_URL=https://your-domain.com/payment-webhook
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8443

# API сервер
API_BASE_URL=https://checkmateai.ru
```

**Сохраните файл:** `Ctrl+X`, затем `Y`, затем `Enter`

### 6. Установка и запуск сервиса

```bash
# Устанавливаем systemd сервис
sudo ./setup_service.sh
```

### 7. Проверка работы

```bash
# Проверяем статус бота
systemctl status checkmate-bot

# Смотрим логи в реальном времени
journalctl -u checkmate-bot -f
```

## Полезные команды для управления

### Управление ботом

```bash
# Перезапустить бота
sudo systemctl restart checkmate-bot

# Остановить бота
sudo systemctl stop checkmate-bot

# Запустить бота
sudo systemctl start checkmate-bot

# Посмотреть статус
systemctl status checkmate-bot
```

### Мониторинг логов

```bash
# Последние 50 строк логов
journalctl -u checkmate-bot -n 50

# Логи в реальном времени
journalctl -u checkmate-bot -f

# Логи за последний час
journalctl -u checkmate-bot --since "1 hour ago"
```

### Обновление кода

```bash
cd /home/CheckMate

# Остановить бота
sudo systemctl stop checkmate-bot

# Обновить код (если через Git)
git pull

# Запустить бота
sudo systemctl start checkmate-bot
```

## Настройка домена (опционально)

### 1. Установка Nginx

```bash
apt install -y nginx

# Создаем конфигурацию
nano /etc/nginx/sites-available/checkmate-bot
```

**Конфигурация Nginx:**

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
ln -s /etc/nginx/sites-available/checkmate-bot /etc/nginx/sites-enabled/

# Проверяем конфигурацию
nginx -t

# Перезапускаем Nginx
systemctl restart nginx
```

### 2. SSL сертификат

```bash
# Устанавливаем Certbot
apt install -y certbot python3-certbot-nginx

# Получаем SSL сертификат
certbot --nginx -d ваш-домен.com

# Автоматическое обновление сертификата
crontab -e
# Добавляем строку:
0 12 * * * /usr/bin/certbot renew --quiet
```

## Автоматический мониторинг

**Добавьте в cron для автоматического перезапуска при сбоях:**

```bash
crontab -e

# Добавьте строку (проверка каждые 5 минут):
*/5 * * * * systemctl is-active --quiet checkmate-bot || systemctl restart checkmate-bot
```

## Диагностика проблем

### Бот не запускается

1. Проверьте логи:

   ```bash
   journalctl -u checkmate-bot -n 100
   ```

2. Проверьте .env файл:

   ```bash
   cat .env
   ```

3. Проверьте права доступа:
   ```bash
   ls -la /home/CheckMate/
   ```

### Проблемы с зависимостями

```bash
cd /home/CheckMate
source venv/bin/activate
pip install -r requirements.txt
```

### Проблемы с webhook

1. Проверьте порт 8443:

   ```bash
   netstat -tulpn | grep 8443
   ```

2. Проверьте Nginx (если установлен):
   ```bash
   nginx -t
   systemctl status nginx
   ```

## 🎉 Готово!

После выполнения всех шагов ваш бот должен работать на сервере Timeweb!

**Для проверки отправьте `/start` вашему боту в Telegram.**
