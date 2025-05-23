# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Создаем директорию для логов
RUN mkdir -p /app/logs

# Создаем непривилегированного пользователя
RUN useradd --create-home --shell /bin/bash checkmate
RUN chown -R checkmate:checkmate /app
USER checkmate

# Указываем порт
EXPOSE 8443

# Команда запуска
CMD ["python", "webhook_server.py"] 