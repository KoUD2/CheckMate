# 🚀 Быстрый деплой CheckMate Bot

## ⚡ TL;DR - Быстрый старт

```bash
# 1. Клонируем репозиторий
git clone https://github.com/your-username/checkmate-bot.git
cd checkmate-bot

# 2. Настраиваем конфигурацию
cp env.example .env
nano .env  # Заполните API ключи

# 3. Деплоим
chmod +x deploy.sh
./deploy.sh

# 4. Проверяем
curl http://localhost:8443/health
```

## 📋 Необходимые API ключи

В файле `.env` обязательно укажите:

```bash
TELEGRAM_BOT_TOKEN=ваш_токен_от_botfather
GEMINI_API_KEY=ваш_ключ_gemini_api
OCR_API_KEY=ваш_ключ_ocr_space
```

## 🔧 Управление сервисом

```bash
# Запуск
make start

# Остановка
make stop

# Перезапуск
make restart

# Логи
make logs

# Статус
make status

# Полный деплой
make deploy
```

## 🆘 Если что-то пошло не так

```bash
# Смотрим логи
docker-compose logs

# Проверяем статус
docker-compose ps

# Перезапускаем
docker-compose restart

# Полная перестройка
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 📞 Поддержка

- 📋 **Полная документация**: [DEPLOY_PRODUCTION.md](DEPLOY_PRODUCTION.md)
- 🐛 **Проблемы**: Создайте issue в репозитории
- 💬 **Telegram Bot API**: https://core.telegram.org/bots/api

---

**🎉 Готово! Ваш CheckMate Bot запущен и готов к работе!**
