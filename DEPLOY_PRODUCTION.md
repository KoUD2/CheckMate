# 🚀 Деплой CheckMate Bot в продакшн

## 📋 Предварительные требования

### Системные требования

- **ОС**: Ubuntu 20.04+ / CentOS 8+ / Debian 10+
- **RAM**: минимум 2GB (рекомендуется 4GB)
- **CPU**: минимум 2 cores
- **Диск**: минимум 10GB свободного места
- **Docker**: версия 20.10+
- **Docker Compose**: версия 2.0+

### API ключи

Перед деплоем убедитесь, что у вас есть:

- ✅ **Telegram Bot Token** (от @BotFather)
- ✅ **Gemini API Key** (Google AI Studio)
- ✅ **OCR.space API Key** (https://ocr.space)
- ⚠️ **YooKassa credentials** (опционально, для платежей)

## 🛠️ Установка Docker

### Ubuntu/Debian

```bash
# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавляем пользователя в группу docker
sudo usermod -aG docker $USER

# Устанавливаем Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Перезагружаемся для применения изменений
sudo reboot
```

### CentOS/RHEL

```bash
# Устанавливаем Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io

# Запускаем Docker
sudo systemctl start docker
sudo systemctl enable docker

# Добавляем пользователя в группу docker
sudo usermod -aG docker $USER

# Устанавливаем Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## 📥 Загрузка и настройка

```bash
# Клонируем репозиторий
git clone https://github.com/your-username/checkmate-bot.git
cd checkmate-bot

# Создаем конфигурацию
cp env.example .env

# Редактируем конфигурацию
nano .env
```

### Конфигурация .env

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHijklmnoPQRstuvWXyz

# Gemini AI API Configuration
GEMINI_API_KEY=AIzaSyC...

# OCR.space API Configuration
OCR_API_KEY=K12345678...
OCR_API_URL=https://api.ocr.space/parse/image

# YooKassa Payment Configuration (опционально)
YOOKASSA_SHOP_ID=123456
YOOKASSA_SECRET_KEY=test_...

# Webhook Configuration
WEBHOOK_URL=https://your-domain.com
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8443

# Backend API Configuration
API_BASE_URL=https://checkmateai.ru

# Environment
ENVIRONMENT=production
```

## 🚀 Деплой

### Автоматический деплой

```bash
# Делаем скрипт исполняемым
chmod +x deploy.sh

# Запускаем деплой
./deploy.sh
```

### Ручной деплой

```bash
# Останавливаем старые контейнеры
docker-compose down --remove-orphans

# Собираем образ
docker-compose build --no-cache

# Запускаем сервис
docker-compose up -d

# Проверяем статус
docker-compose ps
```

## 🔍 Проверка работоспособности

### Health Check

```bash
# Проверяем что сервис отвечает
curl http://localhost:8443/health

# Ожидаемый ответ:
# {"status": "healthy", "service": "checkmate-bot"}
```

### Проверка логов

```bash
# Просмотр логов в реальном времени
docker-compose logs -f

# Просмотр последних 100 строк
docker-compose logs --tail=100

# Просмотр логов конкретного сервиса
docker-compose logs checkmate-bot
```

## 🔧 Управление сервисом

### Основные команды

```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Обновление (с пересборкой)
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Просмотр статуса
docker-compose ps

# Подключение к контейнеру
docker-compose exec checkmate-bot bash
```

### Автозапуск при перезагрузке

Контейнер настроен с `restart: unless-stopped`, поэтому будет автоматически запускаться при перезагрузке системы.

## 🔒 Безопасность

### Firewall настройки

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 8443/tcp    # CheckMate Bot
sudo ufw enable

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --permanent --add-port=8443/tcp
sudo firewall-cmd --reload
```

### SSL/TLS (рекомендуется)

Для продакшн использования рекомендуется настроить SSL/TLS сертификат:

```bash
# Установка Certbot
sudo apt install certbot

# Получение сертификата
sudo certbot certonly --standalone -d your-domain.com

# Настройка автообновления
sudo crontab -e
# Добавить: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 Мониторинг

### Системные ресурсы

```bash
# Использование ресурсов контейнером
docker stats checkmate-bot

# Размер образов
docker images

# Использование дискового пространства
docker system df
```

### Автоматический мониторинг

Добавьте в cron для мониторинга:

```bash
# Открываем crontab
crontab -e

# Добавляем проверку каждые 5 минут
*/5 * * * * curl -f http://localhost:8443/health > /dev/null 2>&1 || docker-compose restart
```

## 🔄 Обновление

### Обновление кода

```bash
# Получаем обновления
git pull origin main

# Пересобираем и перезапускаем
./deploy.sh
```

### Откат к предыдущей версии

```bash
# Смотрим доступные теги
git tag

# Откатываемся к предыдущей версии
git checkout tags/v1.0.0

# Переразворачиваем
./deploy.sh
```

## 🐛 Устранение неполадок

### Контейнер не запускается

```bash
# Проверяем логи
docker-compose logs

# Проверяем конфигурацию
docker-compose config

# Проверяем ресурсы системы
free -h
df -h
```

### Проблемы с API

```bash
# Проверяем доступность API
curl -I https://checkmateai.ru

# Тестируем Gemini API
curl -H "Content-Type: application/json" \
     -H "x-goog-api-key: YOUR_API_KEY" \
     https://generativelanguage.googleapis.com/v1beta/models
```

### Проблемы с сетью

```bash
# Проверяем порты
netstat -tlnp | grep 8443

# Проверяем Docker сети
docker network ls
docker network inspect checkmate_checkmate-network
```

## 📞 Поддержка

При возникновении проблем:

1. 📋 Проверьте логи: `docker-compose logs`
2. 🔍 Проверьте конфигурацию: `.env` файл
3. 🌐 Проверьте сетевые подключения
4. 💬 Обратитесь к документации Telegram Bot API
5. 🆘 Создайте issue в репозитории проекта

---

**Поздравляем! 🎉 CheckMate Bot успешно развернут в продакшене!**
