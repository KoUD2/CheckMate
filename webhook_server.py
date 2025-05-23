import logging
import json
import asyncio
import ssl
from aiohttp import web
from config import WEBHOOK_HOST, WEBHOOK_PORT, setup_logging
from services.payment_callbacks import process_payment_notification, activate_subscription, notify_user_payment_success
from services.api_service import update_user_subscription

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)

app = web.Application()

async def health_check(request):
    """Health check endpoint для мониторинга"""
    return web.Response(text=json.dumps({"status": "healthy", "service": "checkmate-bot"}), status=200)

async def yookassa_webhook(request):
    """Обработчик вебхуков от Юкассы"""
    try:
        data = await request.json()
        logger.info(f"Получен вебхук от Юкассы: {data}")
        
        success = await process_payment_notification(data)
        
        if success:
            return web.Response(text=json.dumps({"status": "success"}), status=200)
        else:
            return web.Response(text=json.dumps({"status": "error", "message": "Could not process payment"}), status=400)
    except json.JSONDecodeError:
        logger.error(f"Ошибка: Получен невалидный JSON в запросе")
        return web.Response(text=json.dumps({"status": "error", "message": "Invalid JSON"}), status=400)
    except Exception as e:
        logger.error(f"Ошибка при обработке вебхука: {e}")
        return web.Response(text=json.dumps({"status": "error", "message": str(e)}), status=500)

async def test_payment_webhook(request):
    """Тестовый обработчик для симуляции вебхуков от Юкассы"""
    try:
        params = request.rel_url.query
        user_id = params.get('user_id')
        status = params.get('status', 'succeeded')
        
        if not user_id:
            return web.Response(text=json.dumps({"error": "user_id is required"}), status=400)

        test_webhook_data = {
            "event": "payment.succeeded" if status == "succeeded" else "payment.canceled",
            "object": {
                "id": f"test_payment_{user_id}",
                "status": status,
                "amount": {
                    "value": "149.00",
                    "currency": "RUB"
                },
                "metadata": {
                    "user_id": user_id
                }
            }
        }
        
        logger.info(f"Тестовый вебхук сгенерирован: {test_webhook_data}")

        success = await process_payment_notification(test_webhook_data)
        
        if success:
            return web.Response(text=json.dumps({"status": "success", "message": "Test webhook processed"}), status=200)
        else:
            return web.Response(text=json.dumps({"status": "error", "message": "Could not process test webhook"}), status=400)
    except Exception as e:
        logger.error(f"Ошибка при обработке тестового вебхука: {e}")
        return web.Response(text=json.dumps({"status": "error", "message": str(e)}), status=500)

async def activate_subscription_manual(request):
    """Ручная активация подписки для отладки"""
    try:
        # Получаем параметры из запроса
        params = request.rel_url.query
        user_id = params.get('user_id')
        days = int(params.get('days', 30))
        
        if not user_id:
            return web.Response(text=json.dumps({"error": "user_id is required"}), status=400)
        
        # Активируем подписку напрямую через API
        user_id = int(user_id)
        api_success = await update_user_subscription(user_id, days)
        
        if api_success:
            logger.info(f"Подписка успешно обновлена через API для пользователя {user_id} на {days} дней")
        else:
            logger.warning(f"Не удалось обновить подписку через API для пользователя {user_id}")
        
        # Активируем подписку локально
        activate_subscription(user_id, days)
        
        # Отправляем уведомление пользователю
        await notify_user_payment_success(user_id)
        
        logger.info(f"Подписка вручную активирована для пользователя {user_id}")
        return web.Response(text=json.dumps({"status": "success", "message": "Subscription activated manually and updated via API"}), status=200)
    except Exception as e:
        logger.error(f"Ошибка при ручной активации подписки: {e}")
        return web.Response(text=json.dumps({"status": "error", "message": str(e)}), status=500)

# Настраиваем middleware для обработки ошибок SSL
@web.middleware
async def error_middleware(request, handler):
    try:
        return await handler(request)
    except web.HTTPException as ex:
        # Обработка HTTP исключений
        logger.warning(f"HTTP exception: {ex.status}, {ex.reason}")
        return web.Response(text=json.dumps({"error": ex.reason}), status=ex.status)
    except Exception as ex:
        # Обработка всех остальных исключений
        logger.error(f"Unexpected error: {ex}")
        return web.Response(text=json.dumps({"error": "Internal server error"}), status=500)

app.middlewares.append(error_middleware)

# Добавляем маршруты
app.router.add_get('/health', health_check)
app.router.add_post('/webhooks/yookassa', yookassa_webhook)
app.router.add_get('/test/payment', test_payment_webhook)
app.router.add_get('/activate/subscription', activate_subscription_manual)

async def start_webhook_server():
    """Запуск сервера для приема вебхуков"""
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Создаем сайт с настройками из конфига
    site = web.TCPSite(runner, WEBHOOK_HOST, WEBHOOK_PORT)
    await site.start()
    
    logger.info(f"Сервер вебхуков запущен на {WEBHOOK_HOST}:{WEBHOOK_PORT}")
    logger.info(f"Health check: http://{WEBHOOK_HOST}:{WEBHOOK_PORT}/health")
    logger.info(f"Для тестирования используйте: http://{WEBHOOK_HOST}:{WEBHOOK_PORT}/test/payment?user_id=YOUR_USER_ID&status=succeeded|canceled")
    logger.info(f"Для ручной активации подписки: http://{WEBHOOK_HOST}:{WEBHOOK_PORT}/activate/subscription?user_id=YOUR_USER_ID&days=30")
    
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Получен сигнал завершения")
    finally:
        await runner.cleanup()

def run_webhook_server():
    """Запуск сервера в отдельном потоке"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_webhook_server())

if __name__ == "__main__":
    asyncio.run(start_webhook_server()) 