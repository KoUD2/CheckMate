#!/bin/bash

echo "🔍 Проверка готовности к деплою CheckMate Bot..."
echo "=================================================="

# Счетчик ошибок
errors=0

# Проверяем наличие необходимых файлов
echo "📁 Проверка файлов проекта:"

required_files=(
    "main.py"
    "webhook_server.py" 
    "config.py"
    "requirements.txt"
    "Dockerfile"
    "docker-compose.yml"
    ".env"
    "handlers/conversation_handlers.py"
    "services/gemini_service.py"
    "services/api_service.py"
    "utils/task37_parser.py"
    "utils/task38_parser.py"
    "services/image_service.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file - ОТСУТСТВУЕТ"
        ((errors++))
    fi
done

# Проверяем наличие директории prompts и файлов в ней
echo ""
echo "📝 Проверка промптов:"

if [ -d "prompts" ]; then
    echo "  ✅ Директория prompts существует"
    
    # Проверяем наличие файлов промптов
    prompt_files=(
        "prompts/prompt1.txt"
        "prompts/prompt2.txt" 
        "prompts/prompt3.txt"
        "prompts/prompt38_1.txt"
        "prompts/prompt38_2.txt"
        "prompts/prompt38_3.txt"
        "prompts/prompt38_4.txt"
        "prompts/prompt38_5.txt"
    )
    
    for file in "${prompt_files[@]}"; do
        if [ -f "$file" ]; then
            echo "  ✅ $file"
        else
            echo "  ❌ $file - ОТСУТСТВУЕТ"
            ((errors++))
        fi
    done
else
    echo "  ❌ Директория prompts - ОТСУТСТВУЕТ"
    ((errors++))
fi

# Проверяем переменные окружения
echo ""
echo "🔐 Проверка переменных окружения:"

if [ -f ".env" ]; then
    source .env
    
    required_vars=("TELEGRAM_BOT_TOKEN" "GEMINI_API_KEY" "OCR_API_KEY")
    
    for var in "${required_vars[@]}"; do
        if [ -n "${!var}" ]; then
            echo "  ✅ $var установлена"
        else
            echo "  ❌ $var - НЕ УСТАНОВЛЕНА"
            ((errors++))
        fi
    done
    
    # Проверяем опциональные переменные
    optional_vars=("YOOKASSA_SHOP_ID" "YOOKASSA_SECRET_KEY" "WEBHOOK_URL")
    echo ""
    echo "  📋 Опциональные переменные:"
    for var in "${optional_vars[@]}"; do
        if [ -n "${!var}" ]; then
            echo "    ✅ $var установлена"
        else
            echo "    ⚠️  $var не установлена (опционально)"
        fi
    done
else
    echo "  ❌ Файл .env - ОТСУТСТВУЕТ"
    echo "     Создайте его: cp env.example .env"
    ((errors++))
fi

# Проверяем наличие Docker
echo ""
echo "🐳 Проверка Docker:"

if command -v docker &> /dev/null; then
    echo "  ✅ Docker установлен: $(docker --version)"
else
    echo "  ❌ Docker не установлен"
    ((errors++))
fi

if command -v docker-compose &> /dev/null; then
    echo "  ✅ Docker Compose установлен: $(docker-compose --version)"
else
    echo "  ❌ Docker Compose не установлен"
    ((errors++))
fi

# Проверяем права доступа к скриптам
echo ""
echo "📜 Проверка исполняемых файлов:"

executable_files=("deploy.sh")

for file in "${executable_files[@]}"; do
    if [ -f "$file" ]; then
        if [ -x "$file" ]; then
            echo "  ✅ $file исполняемый"
        else
            echo "  ⚠️  $file не исполняемый (chmod +x $file)"
        fi
    else
        echo "  ❌ $file отсутствует"
        ((errors++))
    fi
done

# Проверяем конфигурацию docker-compose
echo ""
echo "🔧 Проверка конфигурации Docker Compose:"

if [ -f "docker-compose.yml" ]; then
    if docker-compose config > /dev/null 2>&1; then
        echo "  ✅ Конфигурация docker-compose валидна"
    else
        echo "  ❌ Ошибка в конфигурации docker-compose"
        ((errors++))
    fi
fi

# Итоговый результат
echo ""
echo "=================================================="

if [ $errors -eq 0 ]; then
    echo "🎉 ВСЕ ПРОВЕРКИ ПРОШЛИ УСПЕШНО!"
    echo ""
    echo "🚀 Готов к деплою! Запустите:"
    echo "   ./deploy.sh"
    echo ""
    echo "📋 Или используйте Make команды:"
    echo "   make deploy"
    exit 0
else
    echo "❌ НАЙДЕНЫ ОШИБКИ: $errors"
    echo ""
    echo "🔧 Исправьте указанные проблемы перед деплоем."
    echo ""
    echo "📚 Документация:"
    echo "   - QUICK_DEPLOY.md - быстрый старт"
    echo "   - DEPLOY_PRODUCTION.md - полная документация"
    exit 1
fi 