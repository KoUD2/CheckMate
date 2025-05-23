.PHONY: help build start stop restart logs status clean deploy health test

# Default target
help:
	@echo "🚀 CheckMate Bot Management Commands"
	@echo ""
	@echo "📦 Docker Commands:"
	@echo "  build     - Собрать Docker образ"
	@echo "  start     - Запустить сервис"
	@echo "  stop      - Остановить сервис"
	@echo "  restart   - Перезапустить сервис"
	@echo "  status    - Показать статус контейнеров"
	@echo "  logs      - Показать логи"
	@echo "  clean     - Очистить неиспользуемые образы и контейнеры"
	@echo ""
	@echo "🔧 Deployment Commands:"
	@echo "  deploy    - Полный деплой (build + start)"
	@echo "  health    - Проверить health check"
	@echo "  test      - Запустить тесты"
	@echo ""
	@echo "📋 Configuration:"
	@echo "  config    - Проверить конфигурацию docker-compose"
	@echo "  env       - Показать пример .env файла"

# Docker commands
build:
	@echo "🏗️  Собираем Docker образ..."
	docker-compose build --no-cache

start:
	@echo "🚀 Запускаем сервис..."
	docker-compose up -d

stop:
	@echo "🛑 Останавливаем сервис..."
	docker-compose down

restart: stop start

status:
	@echo "📊 Статус контейнеров:"
	docker-compose ps

logs:
	@echo "📋 Логи сервиса:"
	docker-compose logs --tail=50

logs-follow:
	@echo "📋 Логи в реальном времени:"
	docker-compose logs -f

clean:
	@echo "🧹 Очищаем неиспользуемые ресурсы..."
	docker system prune -f
	docker volume prune -f

# Deployment commands
deploy: stop build start
	@echo "⏳ Ждем запуска сервиса..."
	@sleep 10
	@make health
	@make status

health:
	@echo "🔍 Проверяем health check..."
	@curl -f http://localhost:8443/health > /dev/null 2>&1 && echo "✅ Health check OK" || echo "❌ Health check FAILED"

test:
	@echo "🧪 Запускаем тесты..."
	@if [ -f "test_image_conversion.py" ]; then python test_image_conversion.py; fi

# Configuration commands
config:
	@echo "⚙️  Проверяем конфигурацию:"
	docker-compose config

env:
	@echo "📝 Пример .env файла:"
	@cat env.example

# Development commands
shell:
	@echo "🐚 Подключаемся к контейнеру..."
	docker-compose exec checkmate-bot bash

dev:
	@echo "🔧 Запуск в режиме разработки..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Backup commands
backup:
	@echo "💾 Создаем резервную копию логов..."
	@mkdir -p backups
	@cp checkmate.log backups/checkmate-$(shell date +%Y%m%d-%H%M%S).log
	@echo "✅ Резервная копия создана в backups/"

# Monitoring commands
stats:
	@echo "📊 Статистика использования ресурсов:"
	docker stats checkmate-bot --no-stream

top:
	@echo "⚡ Процессы в контейнере:"
	docker-compose top 