import os
import asyncio
import aiohttp
import argparse
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Константы
class Config:
    BATCH_SIZE = 100
    TIMEOUT = 30
    CONNECT_TIMEOUT = 10
    RETRY_TIMEOUT = 60
    RETRY_CONNECT_TIMEOUT = 15
    RETRY_DELAY = 0.1
    PIM_BASE_URL = "https://pim.uroven.pro/pictures/originals/"
    DEFAULT_EXT = "JPG"


def load_config() -> Dict[str, str]:
    """Загрузка и валидация переменных окружения"""
    load_dotenv()

    required_vars = [
        "PIM_API_URL",
        "PIM_LOGIN",
        "PIM_PASSWORD",
        "SUPABASE_URL",
        "SUPABASE_KEY",
    ]
    config = {}

    for var in required_vars:
        value = os.getenv(var)
        if not value:
            raise ValueError(f"Переменная окружения {var} не установлена")
        config[var] = value

    return config


def get_supabase_client() -> Client:
    """Безопасная инициализация Supabase клиента"""
    config = load_config()
    return create_client(config["SUPABASE_URL"], config["SUPABASE_KEY"])


def extract_file_extension(img_type: Optional[str]) -> str:
    """Извлечение расширения файла из типа изображения"""
    if not img_type:
        return Config.DEFAULT_EXT

    if "/" in img_type:
        return img_type.split("/")[-1].upper()
    return img_type.upper()


async def retry_with_backoff(
    func, max_retries: int = 3, initial_delay: float = 1
) -> Any:
    """Retry функция с экспоненциальной задержкой"""
    for attempt in range(max_retries):
        try:
            result = await func()
            if result is not None:
                return result
        except (
            aiohttp.ClientError,
            aiohttp.ServerTimeoutError,
            asyncio.TimeoutError,
        ) as e:
            if attempt == max_retries - 1:
                raise e
            delay = initial_delay * (2**attempt)
            logger.warning(
                f"Попытка {attempt + 1} не удалась, повтор через {delay}с: {e}"
            )
            await asyncio.sleep(delay)

    raise Exception("Все попытки исчерпаны")


async def authorize_pim(config: Dict[str, str]) -> str:
    """Авторизация в PIM API"""
    auth_url = f"{config['PIM_API_URL']}/sign-in/"
    payload = {
        "login": config["PIM_LOGIN"],
        "password": config["PIM_PASSWORD"],
        "remember": True,
    }
    timeout = aiohttp.ClientTimeout(
        total=Config.TIMEOUT, connect=Config.CONNECT_TIMEOUT
    )

    async def auth_request():
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(auth_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        return data["data"]["access"]["token"]
                raise Exception(f"Ошибка авторизации: {response.status}")

    return await retry_with_backoff(auth_request)


def get_products_from_supabase(
    max_products: Optional[int] = None,
) -> List[Dict[str, str]]:
    """Получение всех товаров из Supabase для полного обновления"""
    supabase = get_supabase_client()
    # Получаем ВСЕ записи без фильтров
    query = supabase.table("product_images").select(
        "product_id, product_code_1c, id, image_type"
    )

    if max_products:
        query = query.limit(max_products)

    response = query.execute()
    if not response.data:
        logger.warning("Товары не найдены в Supabase")
        return []

    # Преобразуем в нужный формат, берем уникальные товары
    products = []
    seen_products = set()
    for item in response.data:
        product_id = item.get("product_id")
        if product_id not in seen_products:
            products.append(
                {
                    "id": product_id,
                    "code_1c": item.get("product_code_1c", ""),
                    "record_id": item.get("id"),  # ID записи в таблице для обновления
                }
            )
            seen_products.add(product_id)

    logger.info(f"Получено {len(products)} товаров для полного обновления из Supabase")
    return products


def create_image_url(picture: Dict[str, Any]) -> str:
    """Создание URL изображения"""
    ext = extract_file_extension(picture.get("type"))
    image_name = f"{picture['name']}.{ext}"
    return f"{Config.PIM_BASE_URL}{image_name}"


def create_update_object(
    record_id: int,
    main_picture: Dict[str, Any] = None,
    additional_pictures: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Создание объекта для полного обновления записи с основным и дополнительными изображениями"""
    update_data = {"id": record_id}

    # Основное изображение
    if main_picture and main_picture.get("name"):
        ext = extract_file_extension(main_picture.get("type"))
        image_name = f"{main_picture['name']}.{ext}"
        main_image_url = f"{Config.PIM_BASE_URL}{image_name}"

        update_data.update(
            {
                "image_name": image_name,
                "image_url": main_image_url,
                "picture_id": str(main_picture.get("id", "")),
            }
        )

    # Дополнительные изображения
    additional_image_urls = []
    additional_picture_ids = []
    if additional_pictures:
        for pic in additional_pictures:
            if pic and pic.get("name"):
                additional_image_urls.append(create_image_url(pic))
                if pic.get("id"):
                    additional_picture_ids.append(str(pic.get("id")))

    update_data.update(
        {
            "additional_image_urls": (
                ",".join(additional_image_urls) if additional_image_urls else None
            ),
            "additional_picture_ids": (
                ",".join(additional_picture_ids) if additional_picture_ids else None
            ),
        }
    )

    return update_data


async def get_product_images(
    session: aiohttp.ClientSession,
    token: str,
    product: Dict[str, str],
    config: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Получение всех изображений товара из PIM API для полного обновления"""
    product_id = product["id"]
    record_id = product.get("record_id")
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{config['PIM_API_URL']}/product/{product_id}"

    async def get_images():
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                logger.warning(
                    f"Ошибка получения товара {product_id}: {response.status}"
                )
                return []

            data = await response.json()
            if not data.get("success"):
                logger.warning(f"Неуспешный ответ для товара {product_id}")
                return []

            product_data = data["data"]
            result = []

            # Основное изображение
            main_picture = product_data.get("picture")

            # Дополнительные изображения
            additional_pictures = [
                pic
                for pic in product_data.get("pictures", [])
                if pic and pic.get("name")
            ]

            # Создаем объект для полного обновления записи
            update_obj = create_update_object(
                record_id, main_picture, additional_pictures
            )
            result.append(update_obj)

            main_info = (
                "есть основное"
                if main_picture and main_picture.get("name")
                else "НЕТ основного"
            )
            logger.info(
                f"Товар {product_id}: {main_info}, {len(additional_pictures)} дополнительных изображений"
            )

            return result

    try:
        return await retry_with_backoff(get_images)
    except Exception as e:
        logger.error(f"Ошибка запроса товара {product_id}: {e}")
        return []


async def process_batch(
    token: str,
    products_batch: List[Dict[str, str]],
    batch_num: int,
    config: Dict[str, str],
) -> int:
    """Обработка партии товаров"""
    logger.info(f"Обработка партии {batch_num}: {len(products_batch)} товаров")

    timeout = aiohttp.ClientTimeout(
        total=Config.RETRY_TIMEOUT, connect=Config.RETRY_CONNECT_TIMEOUT
    )
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [
            get_product_images(session, token, product, config)
            for product in products_batch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_images = []
        for result in results:
            if isinstance(result, list):
                all_images.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Ошибка обработки: {result}")

        if not all_images:
            return 0

        # Параллельное обновление записей в Supabase
        supabase = get_supabase_client()
        updated_count = 0

        def update_single_record(image_update, retry_count=3):
            """Обновление одной записи с retry"""
            import time

            record_id = image_update["id"]
            update_data = {k: v for k, v in image_update.items() if k != "id"}

            for attempt in range(retry_count):
                try:
                    result = (
                        supabase.table("product_images")
                        .update(update_data)
                        .eq("id", record_id)
                        .execute()
                    )
                    return 1 if result.data else 0
                except Exception as e:
                    if attempt == retry_count - 1:
                        logger.error(
                            f"Ошибка при обновлении записи {record_id} (финальная попытка): {e}"
                        )
                        return 0
                    # Пауза перед retry
                    time.sleep(0.2 * (attempt + 1))
            return 0

        # Обновляем последовательно с небольшими паузами для стабильности
        updated_count = 0
        for i, image_update in enumerate(all_images):
            result = update_single_record(image_update)
            updated_count += result
            # Небольшая пауза каждые 10 запросов
            if i % 10 == 9:
                import time

                time.sleep(0.1)

        logger.info(f"Партия {batch_num}: обновлено {updated_count} записей")
        return updated_count


async def main(
    batch_size: int = 100, max_products: Optional[int] = None, max_concurrent: int = 3
) -> None:
    """Основная функция"""
    try:
        # Загружаем конфигурацию
        config = load_config()

        # Авторизация
        token = await authorize_pim(config)
        logger.info("Авторизация в PIM API успешна")

        # Получение товаров из Supabase
        products = get_products_from_supabase(max_products)
        if not products:
            return

        logger.info(f"Начинаем обработку {len(products)} товаров")

        # Обработка партиями с семафором
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []

        for i in range(0, len(products), batch_size):
            batch = products[i : i + batch_size]
            batch_num = i // batch_size + 1

            async def process_batch_with_limit(batch_data, batch_number):
                async with semaphore:
                    result = await process_batch(
                        token, batch_data, batch_number, config
                    )
                    await asyncio.sleep(0.05)  # Минимальная пауза
                    return result

            tasks.append(process_batch_with_limit(batch, batch_num))

        # Выполнение всех задач
        results = await asyncio.gather(*tasks)
        total_saved = sum(results)

        logger.info(
            f"Завершено! Обработано {len(products)} товаров, обновлено {total_saved} записей"
        )

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Получение данных об изображениях товаров"
    )
    parser.add_argument(
        "--batch-size", type=int, default=100, help="Размер партии товаров"
    )
    parser.add_argument(
        "--max-products", type=int, default=None, help="Максимальное количество товаров"
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=3,
        help="Максимальное количество одновременных партий",
    )
    args = parser.parse_args()

    asyncio.run(
        main(
            batch_size=args.batch_size,
            max_products=args.max_products,
            max_concurrent=args.max_concurrent,
        )
    )
