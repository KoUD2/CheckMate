import logging
import aiohttp
import json
from datetime import datetime, timedelta
import re
import ssl

# Настройка логирования
logger = logging.getLogger(__name__)

# URL API для регистрации пользователей
API_BASE_URL = "https://checkmateai.ru"
REGISTER_USER_URL = f"{API_BASE_URL}/tgusers"
GET_USER_URL = f"{API_BASE_URL}/tgusers" # Базовый URL для получения данных о пользователе
UPDATE_SUBSCRIPTION_URL = f"{API_BASE_URL}/tgusers" # Базовый URL для обновления подписки
UPDATE_FREE_CHECKS_URL = f"{API_BASE_URL}/tgusers" # Базовый URL для обновления бесплатных проверок

# Создаем SSL контекст с отключенной проверкой хоста
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

async def register_user(tg_id: int, username: str) -> bool:
    """
    Регистрирует пользователя в системе через API.
    Сначала проверяет, существует ли пользователь, и регистрирует только если его нет.

    Args:
        tg_id: ID пользователя в Telegram
        username: Имя пользователя в Telegram

    Returns:
        bool: True если пользователь существует или успешно зарегистрирован, False в случае ошибки
    """
    # Проверяем входные данные
    if not tg_id:
        logger.error(f"Ошибка при регистрации пользователя: не указан tg_id")
        return False

    try:
        # Сначала проверяем, существует ли пользователь
        logger.info(f"Проверяем, существует ли пользователь {tg_id}")
        user_data = await get_user_subscription(tg_id)

        if user_data:
            # Пользователь уже существует
            logger.info(f"Пользователь {tg_id} уже зарегистрирован в системе")
            return True

        # Пользователь не существует, регистрируем его
        logger.info(f"Пользователь {tg_id} не найден, начинаем регистрацию")

        # Подготавливаем данные для запроса
        registration_data = {
            "tg_id": tg_id,
            "username": username or "unknown"  # Если имя пользователя не указано, используем "unknown"
        }

        # Отправляем POST запрос с отключенной проверкой SSL
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.post(REGISTER_USER_URL, json=registration_data) as response:
                response_text = await response.text()

                # Проверяем статус ответа
                if response.status == 200:
                    logger.info(f"Пользователь {tg_id} успешно зарегистрирован")
                    return True
                elif response.status == 400:
                    # Проверяем, является ли ошибка результатом того, что пользователь уже существует
                    try:
                        response_json = json.loads(response_text)
                        if "already exists" in response_json.get("detail", "").lower():
                            logger.info(f"Пользователь {tg_id} уже зарегистрирован (получен статус 400)")
                            return True
                    except:
                        pass

                logger.error(f"Ошибка при регистрации пользователя {tg_id}: {response.status}, {response_text}")
                return False

    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя {tg_id}: {e}")
        return False

async def get_user_subscription(tg_id: int) -> dict:
    """
    Получает информацию о подписке пользователя.
    При ошибках API использует локальную проверку подписки.

    Args:
        tg_id: ID пользователя в Telegram

    Returns:
        dict: Данные о подписке пользователя или None в случае ошибки
    """
    if not tg_id:
        logger.error("Ошибка при получении данных о подписке: не указан tg_id")
        return None

    try:
        # Формируем URL для запроса
        user_url = f"{GET_USER_URL}/{tg_id}"

        # Отправляем GET запрос с отключенной проверкой SSL
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.get(user_url) as response:
                # Проверяем статус ответа
                if response.status == 200:
                    # Получаем данные о пользователе
                    user_data = await response.json()
                    logger.info(f"Получены данные о подписке пользователя {tg_id}: {user_data}")
                    return user_data
                elif response.status == 404:
                    logger.warning(f"⚠️ API endpoint не найден (404) для пользователя {tg_id}. Используем локальную проверку.")
                    return await get_local_subscription_fallback(tg_id)
                else:
                    response_text = await response.text()
                    logger.error(f"Ошибка при получении данных о подписке пользователя {tg_id}: {response.status}, {response_text}")
                    logger.info(f"Используем локальную проверку для пользователя {tg_id}")
                    return await get_local_subscription_fallback(tg_id)
    except aiohttp.ClientConnectorError as e:
        logger.error(f"❌ Ошибка подключения к API при получении данных пользователя {tg_id}: {e}")
        logger.info(f"Используем локальную проверку для пользователя {tg_id}")
        return await get_local_subscription_fallback(tg_id)
    except aiohttp.ClientTimeout as e:
        logger.error(f"❌ Таймаут при получении данных пользователя {tg_id}: {e}")
        logger.info(f"Используем локальную проверку для пользователя {tg_id}")
        return await get_local_subscription_fallback(tg_id)
    except Exception as e:
        logger.error(f"Ошибка при получении данных о подписке пользователя {tg_id}: {e}")
        logger.info(f"Используем локальную проверку для пользователя {tg_id}")
        return await get_local_subscription_fallback(tg_id)

async def get_local_subscription_fallback(tg_id: int) -> dict:
    """
    Fallback функция для получения данных о подписке из локального хранилища.

    Args:
        tg_id: ID пользователя в Telegram

    Returns:
        dict: Данные о подписке пользователя в формате API или None
    """
    try:
        # Импортируем локальное хранилище подписок
        from services.payment_callbacks import get_all_active_subscriptions
        from datetime import datetime
        
        local_subscriptions = get_all_active_subscriptions()
        local_subscription = local_subscriptions.get(tg_id)
        
        if local_subscription and local_subscription.get("is_active"):
            # Проверяем не истекла ли локальная подписка
            expiry_date = local_subscription.get("expiry_date")
            if expiry_date and expiry_date > datetime.now():
                # Формируем данные в формате API
                api_format_data = {
                    "IsActive": True,
                    "SubUntil": expiry_date.isoformat(),
                    "FreeChecksLeft": 0  # При активной подписке не важно
                }
                logger.info(f"Найдена активная локальная подписка для пользователя {tg_id}")
                return api_format_data
        
        # Если локальной подписки нет или она истекла
        logger.info(f"Локальная подписка не найдена или истекла для пользователя {tg_id}")
        return None
        
    except Exception as e:
        logger.error(f"Ошибка при получении локальной подписки для пользователя {tg_id}: {e}")
        return None

def calculate_days_left(sub_until: str) -> int:
    """
    Вычисляет количество дней, оставшихся до истечения подписки.

    Args:
        sub_until: Дата истечения подписки в формате строки

    Returns:
        int: Количество дней до истечения подписки или 0, если не удалось определить
    """
    try:
        # Проверяем несколько возможных форматов даты
        date_formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO формат с миллисекундами
            "%Y-%m-%dT%H:%M:%SZ",      # ISO формат без миллисекунд
            "%Y-%m-%d",                # Только дата
            "%d.%m.%Y"                 # Русский формат даты
        ]

        for date_format in date_formats:
            try:
                expiry_date = datetime.strptime(sub_until, date_format)
                now = datetime.now()

                # Вычисляем разницу в днях
                days_left = (expiry_date - now).days

                # Если дата истечения в прошлом, возвращаем 0
                return max(days_left, 0)
            except ValueError:
                continue

        # Если ни один формат не подошел, пробуем извлечь дату из строки
        # Например, из "2024-05-30T14:30:45.123Z" извлечем "2024-05-30"
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', sub_until)
        if date_match:
            date_str = date_match.group(1)
            expiry_date = datetime.strptime(date_str, "%Y-%m-%d")
            now = datetime.now()
            days_left = (expiry_date - now).days
            return max(days_left, 0)

        logger.error(f"Не удалось распознать формат даты: {sub_until}")
        return 0
    except Exception as e:
        logger.error(f"Ошибка при расчете дней до истечения подписки: {e}")
        return 0

async def update_user_subscription(tg_id: int, days: int = 30) -> bool:
    """
    Обновляет статус подписки пользователя через API.

    Args:
        tg_id: ID пользователя в Telegram
        days: Количество дней действия подписки (по умолчанию 30)

    Returns:
        bool: True если обновление успешно, False в случае ошибки
    """
    if not tg_id:
        logger.error("Ошибка при обновлении подписки: не указан tg_id")
        return False

    try:
        # Формируем URL для запроса
        subscription_url = f"{UPDATE_SUBSCRIPTION_URL}/{tg_id}/subscription"

        # Создаем дату окончания подписки (текущая дата + указанное количество дней)
        # RFC3339 формат с правильным timezone
        from datetime import timezone
        sub_until_date = datetime.now(timezone.utc) + timedelta(days=days)
        sub_until = sub_until_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # Подготавливаем данные для запроса
        subscription_data = {
            "is_active": True,
            "sub_until": sub_until
        }

        logger.info(f"Обновление подписки для пользователя {tg_id}")
        logger.info(f"URL: {subscription_url}")
        logger.info(f"Данные: {subscription_data}")

        # Отправляем PATCH запрос с отключенной проверкой SSL
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.patch(subscription_url, json=subscription_data) as response:
                # Логируем ответ сервера
                response_text = await response.text()
                logger.info(f"Статус ответа: {response.status}")
                logger.info(f"Ответ сервера: {response_text}")

                # Проверяем статус ответа
                if response.status in [200, 201, 204]:
                    logger.info(f"✅ Подписка пользователя {tg_id} успешно обновлена до {sub_until}")
                    return True
                elif response.status == 404:
                    logger.warning(f"⚠️ API endpoint не найден (404) для пользователя {tg_id}. Подписка будет активирована локально.")
                    return False
                elif response.status == 500:
                    logger.error(f"❌ Ошибка сервера (500) при обновлении подписки пользователя {tg_id}")
                    return False
                else:
                    logger.error(f"❌ Ошибка при обновлении подписки пользователя {tg_id}: {response.status}")
                    logger.error(f"Ответ сервера: {response_text}")
                    return False
    except aiohttp.ClientConnectorError as e:
        logger.error(f"❌ Ошибка подключения к API при обновлении подписки пользователя {tg_id}: {e}")
        return False
    except aiohttp.ClientTimeout as e:
        logger.error(f"❌ Таймаут при обновлении подписки пользователя {tg_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Исключение при обновлении подписки пользователя {tg_id}: {e}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        return False

async def increment_user_free_checks(tg_id: int) -> bool:
    """
    Увеличивает счетчик бесплатных проверок пользователя на 1 через API.

    Args:
        tg_id: ID пользователя в Telegram

    Returns:
        bool: True если обновление успешно, False в случае ошибки
    """
    if not tg_id:
        logger.error("Ошибка при обновлении счетчика бесплатных проверок: не указан tg_id")
        return False

    try:
        # Формируем URL для запроса
        free_checks_url = f"{UPDATE_FREE_CHECKS_URL}/{tg_id}/free_checks"

        # Подготавливаем данные для запроса - увеличиваем на 1
        free_checks_data = {
            "FreeChecksLeft": 1
        }

        logger.info(f"Отправляем запрос на обновление счетчика бесплатных проверок для пользователя {tg_id}")

        # Отправляем PATCH запрос с отключенной проверкой SSL
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.patch(free_checks_url, json=free_checks_data) as response:
                # Проверяем статус ответа
                if response.status in [200, 201, 204]:
                    logger.info(f"Счетчик бесплатных проверок пользователя {tg_id} успешно увеличен на 1")
                    return True
                else:
                    response_text = await response.text()
                    logger.error(f"Ошибка при обновлении счетчика бесплатных проверок пользователя {tg_id}: {response.status}, {response_text}")
                    return False
    except Exception as e:
        logger.error(f"Ошибка при обновлении счетчика бесплатных проверок пользователя {tg_id}: {e}")
        return False

async def decrement_user_free_checks(tg_id: int) -> bool:
    """
    Уменьшает счетчик бесплатных проверок пользователя на 1 через API.
    Не уменьшает, если счетчик уже равен 0.

    Args:
        tg_id: ID пользователя в Telegram

    Returns:
        bool: True если обновление успешно, False в случае ошибки
    """
    if not tg_id:
        logger.error("Ошибка при уменьшении счетчика бесплатных проверок: не указан tg_id")
        return False

    try:
        # Сначала получаем текущее состояние пользователя
        user_data = await get_user_subscription(tg_id)

        if not user_data:
            logger.error(f"Не удалось получить данные пользователя {tg_id} для уменьшения счетчика")
            return False

        current_free_checks = user_data.get("FreeChecksLeft", 0)

        # Если счетчик уже равен 0, не уменьшаем
        if current_free_checks <= 0:
            logger.info(f"Счетчик бесплатных проверок пользователя {tg_id} уже равен {current_free_checks}, не уменьшаем")
            return True

        # Формируем URL для запроса
        free_checks_url = f"{UPDATE_FREE_CHECKS_URL}/{tg_id}/free_checks"

        # Подготавливаем данные для запроса - уменьшаем на 1
        free_checks_data = {
            "FreeChecksLeft": -1
        }

        logger.info(f"Отправляем запрос на уменьшение счетчика бесплатных проверок для пользователя {tg_id} с {current_free_checks} до {current_free_checks - 1}")

        # Отправляем PATCH запрос с отключенной проверкой SSL
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.patch(free_checks_url, json=free_checks_data) as response:
                # Проверяем статус ответа
                if response.status in [200, 201, 204]:
                    logger.info(f"Счетчик бесплатных проверок пользователя {tg_id} успешно уменьшен на 1")
                    return True
                else:
                    response_text = await response.text()
                    logger.error(f"Ошибка при уменьшении счетчика бесплатных проверок пользователя {tg_id}: {response.status}, {response_text}")
                    return False
    except Exception as e:
        logger.error(f"Ошибка при уменьшении счетчика бесплатных проверок пользователя {tg_id}: {e}")
        return False

async def can_user_proceed_with_check(tg_id: int) -> dict:
    """
    Проверяет, может ли пользователь продолжить с анализом задания
    на основе количества оставшихся бесплатных проверок и статуса подписки.

    Args:
        tg_id: ID пользователя в Telegram

    Returns:
        dict: Словарь с ключами:
            - can_proceed (bool): True если пользователь может продолжить, False если нет
            - reason (str): Причина, если пользователь не может продолжить
            - FreeChecksLeft (int): Количество оставшихся бесплатных проверок
            - is_subscription_active (bool): Активна ли подписка
    """
    if not tg_id:
        logger.error("Ошибка при проверке возможности анализа: не указан tg_id")
        return {"can_proceed": False, "reason": "Ошибка идентификации пользователя"}

    try:
        # Сначала проверяем локальные подписки (активные платежи)
        from services.payment_callbacks import get_all_active_subscriptions
        from datetime import datetime

        local_subscriptions = get_all_active_subscriptions()
        local_subscription = local_subscriptions.get(tg_id)

        is_subscription_active = False

        if local_subscription and local_subscription.get("is_active"):
            # Проверяем не истекла ли локальная подписка
            expiry_date = local_subscription.get("expiry_date")
            if expiry_date and expiry_date > datetime.now():
                is_subscription_active = True
                logger.info(f"Найдена активная локальная подписка для пользователя {tg_id}")

                # Если есть активная локальная подписка, пользователь может продолжить
                return {
                    "can_proceed": True,
                    "FreeChecksLeft": 0,  # При активной подписке не важно
                    "is_subscription_active": True
                }

        # Если локальной подписки нет, проверяем API
        user_data = await get_user_subscription(tg_id)

        if not user_data:
            logger.error(f"Не удалось получить данные пользователя {tg_id}")
            return {"can_proceed": False, "reason": "Не удалось получить данные пользователя"}

        # Извлекаем нужные поля
        FreeChecksLeft = user_data.get("FreeChecksLeft", 0)
        api_is_active = user_data.get("IsActive", False)

        logger.info(f"Проверка пользователя {tg_id}: FreeChecksLeft={FreeChecksLeft}, API IsActive={api_is_active}, Local Active={is_subscription_active}")

        # Проверяем условия
        if api_is_active:
            # Если подписка активна в API, пользователь всегда может продолжить
            return {
                "can_proceed": True,
                "FreeChecksLeft": FreeChecksLeft,
                "is_subscription_active": True
            }
        elif FreeChecksLeft > 0:
            # Если подписка неактивна, но есть бесплатные проверки
            return {
                "can_proceed": True,
                "FreeChecksLeft": FreeChecksLeft,
                "is_subscription_active": False
            }
        else:
            # Если подписка неактивна и нет бесплатных проверок
            return {
                "can_proceed": False,
                "reason": "Закончились бесплатные проверки. Необходимо оформить подписку",
                "FreeChecksLeft": FreeChecksLeft,
                "is_subscription_active": False
            }

    except Exception as e:
        logger.error(f"Ошибка при проверке возможности анализа для пользователя {tg_id}: {e}")
        return {"can_proceed": False, "reason": f"Произошла ошибка: {str(e)}"}

async def get_auth_token() -> str:
    """
    Получает токен авторизации для отправки данных на API.

    Returns:
        str: Access token или пустая строка в случае ошибки
    """
    try:
        # URL для авторизации
        auth_url = f"{API_BASE_URL}/auth/login"

        # Данные для авторизации (всегда одинаковые)
        auth_data = {
            "password": "botcheckmate",
            "username": "botcheckmate"
        }

        logger.info("Получаем токен авторизации")

        # Отправляем POST запрос для авторизации
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.post(auth_url, json=auth_data) as response:

                # Проверяем статус ответа
                if response.status == 200:
                    auth_response = await response.json()
                    access_token = auth_response.get("access_token", "")

                    if access_token:
                        logger.info("Токен авторизации успешно получен")
                        return access_token
                    else:
                        logger.error("В ответе авторизации отсутствует access_token")
                        return ""
                else:
                    response_text = await response.text()
                    logger.error(f"Ошибка при получении токена авторизации: {response.status}, {response_text}")
                    return ""

    except Exception as e:
        logger.error(f"Ошибка при получении токена авторизации: {e}")
        return ""

async def send_essay_result(essay_data: dict) -> bool:
    """
    Отправляет результат проверки задания 37 (essay) на бэкенд.

    Args:
        essay_data: Данные о проверке эссе в формате:
        {
            "comments": [
                {
                    "criterion": "string",
                    "end_pos": 0,
                    "start_pos": 0,
                    "text": "string"
                }
            ],
            "email": "string",
            "essay": "string",
            "k1": 0,
            "k2": 0,
            "k3": 0,
            "questions_theme": "string",
            "subject": "string"
        }

    Returns:
        bool: True если отправка успешна, False в случае ошибки
    """
    if not essay_data:
        logger.error("Ошибка при отправке результата эссе: данные не предоставлены")
        return False

    try:
        # Сначала получаем токен авторизации
        access_token = await get_auth_token()

        if not access_token:
            logger.error("Не удалось получить токен авторизации для отправки эссе")
            return False

        # URL для отправки результатов эссе
        essays_url = f"{API_BASE_URL}/essays"

        # Подготавливаем заголовки с авторизацией
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        logger.info(f"Отправляем результат проверки эссе на {essays_url}")
        logger.info(f"Данные эссе: email длина={len(essay_data.get('email', ''))}, subject={essay_data.get('subject')}, "
                   f"k1={essay_data.get('k1')}, k2={essay_data.get('k2')}, k3={essay_data.get('k3')}")

        # Отправляем POST запрос с авторизацией
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.post(essays_url, json=essay_data, headers=headers) as response:
                response_text = await response.text()

                # Проверяем статус ответа
                if response.status == 200 or response.status == 201:
                    logger.info(f"Результат проверки эссе успешно отправлен")
                    return True
                else:
                    logger.error(f"Ошибка при отправке результата эссе: {response.status}, {response_text}")
                    return False

    except Exception as e:
        logger.error(f"Ошибка при отправке результата эссе: {e}")
        return False

async def send_table_task_result(table_task_data: dict) -> bool:
    """
    Отправляет результат проверки задания 38 (table task) на бэкенд.

    Args:
        table_task_data: Данные о проверке задания 38 в формате:
        {
            "comments": [
                {
                    "criterion": "string",
                    "end_pos": 0,
                    "start_pos": 0,
                    "text": "string"
                }
            ],
            "essay": "string",
            "k1": 0,
            "k2": 0,
            "k3": 0,
            "k4": 0,
            "k5": 0,
            "opinion": "string",
            "problem": "string",
            "table_image": "string"
        }

    Returns:
        bool: True если отправка успешна, False в случае ошибки
    """
    if not table_task_data:
        logger.error("Ошибка при отправке результата задания 38: данные не предоставлены")
        return False

    try:
        # Сначала получаем токен авторизации
        access_token = await get_auth_token()

        if not access_token:
            logger.error("Не удалось получить токен авторизации для отправки задания 38")
            return False

        # URL для отправки результатов задания 38
        table_tasks_url = f"{API_BASE_URL}/tabletasks"

        # Подготавливаем заголовки с авторизацией
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        logger.info(f"Отправляем результат проверки задания 38 на {table_tasks_url}")
        logger.info(f"Данные задания 38: opinion={table_task_data.get('opinion', '')[:50]}..., "
                   f"problem={table_task_data.get('problem', '')[:50]}..., "
                   f"k1={table_task_data.get('k1')}, k2={table_task_data.get('k2')}, k3={table_task_data.get('k3')}, "
                   f"k4={table_task_data.get('k4')}, k5={table_task_data.get('k5')}")

        # Отправляем POST запрос с авторизацией
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.post(table_tasks_url, json=table_task_data, headers=headers) as response:
                response_text = await response.text()

                # Проверяем статус ответа
                if response.status == 200 or response.status == 201:
                    logger.info(f"Результат проверки задания 38 успешно отправлен")
                    return True
                else:
                    logger.error(f"Ошибка при отправке результата задания 38: {response.status}, {response_text}")
                    return False

    except Exception as e:
        logger.error(f"Ошибка при отправке результата задания 38: {e}")
        return False
