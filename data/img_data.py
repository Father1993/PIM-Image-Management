import os
import asyncio
import aiohttp
import argparse
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Константы
class Config:
    BATCH_SIZE = 100
    TIMEOUT = 30
    CONNECT_TIMEOUT = 10
    RETRY_TIMEOUT = 60
    RETRY_CONNECT_TIMEOUT = 15
    RETRY_DELAY = 0.5
    PIM_BASE_URL = "https://pim.uroven.pro/pictures/originals/"
    DEFAULT_EXT = "JPG"

def load_config() -> Dict[str, str]:
    """Загрузка и валидация переменных окружения"""
    load_dotenv()
    
    required_vars = ["PIM_API_URL", "PIM_LOGIN", "PIM_PASSWORD", "SUPABASE_URL", "SUPABASE_KEY"]
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

async def retry_with_backoff(func, max_retries: int = 3, initial_delay: float = 1) -> Any:
    """Retry функция с экспоненциальной задержкой"""
    for attempt in range(max_retries):
        try:
            result = await func()
            if result is not None:
                return result
        except (aiohttp.ClientError, aiohttp.ServerTimeoutError, asyncio.TimeoutError) as e:
            if attempt == max_retries - 1:
                raise e
            delay = initial_delay * (2 ** attempt)
            logger.warning(f"Попытка {attempt + 1} не удалась, повтор через {delay}с: {e}")
            await asyncio.sleep(delay)
    
    raise Exception("Все попытки исчерпаны")

async def authorize_pim(config: Dict[str, str]) -> str:
    """Авторизация в PIM API"""
    auth_url = f"{config['PIM_API_URL']}/sign-in/"
    payload = {"login": config["PIM_LOGIN"], "password": config["PIM_PASSWORD"], "remember": True}
    timeout = aiohttp.ClientTimeout(total=Config.TIMEOUT, connect=Config.CONNECT_TIMEOUT)
    
    async def auth_request():
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(auth_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        return data["data"]["access"]["token"]
                raise Exception(f"Ошибка авторизации: {response.status}")
    
    return await retry_with_backoff(auth_request)

def get_products_from_supabase(max_products: Optional[int] = None) -> List[Dict[str, str]]:
    """Получение списка товаров из Supabase"""
    supabase = get_supabase_client()
    query = supabase.table('product_images').select('product_id, product_code_1c')
    
    if max_products:
        query = query.limit(max_products * 2)
    
    response = query.execute()
    if not response.data:
        logger.warning("Товары не найдены в Supabase")
        return []
    
    # Удаляем дубликаты по product_id
    unique_products = {}
    for item in response.data:
        product_id = item.get("product_id")
        if product_id and product_id not in unique_products:
            unique_products[product_id] = {
                "id": product_id,
                "code_1c": item.get("product_code_1c", "")
            }
    
    products = list(unique_products.values())
    
    # Ограничиваем количество, если нужно
    if max_products and len(products) > max_products:
        products = products[:max_products]
        
    logger.info(f"Получено {len(products)} товаров из Supabase")
    return products

def create_image_object(product_id: str, product_code_1c: str, picture: Dict[str, Any], image_type: str) -> Dict[str, Any]:
    """Создание объекта изображения"""
    ext = extract_file_extension(picture.get("type"))
    image_name = f"{picture['name']}.{ext}"
    
    return {
        "product_id": product_id,
        "product_code_1c": product_code_1c,
        "image_name": image_name,
        "image_url": f"{Config.PIM_BASE_URL}{image_name}",
        "image_type": image_type,
        "picture_id": picture.get("id"),
        "is_downloaded": False,
        "is_optimized": False,
        "is_uploaded": False,
        "optimized_url": None
    }

async def get_product_images(session: aiohttp.ClientSession, token: str, product: Dict[str, str], config: Dict[str, str]) -> List[Dict[str, Any]]:
    """Получение изображений товара из PIM API"""
    product_id = product['id']
    product_code_1c = product.get('code_1c', '')
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{config['PIM_API_URL']}/product/{product_id}"
    
    async def get_images():
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                logger.warning(f"Ошибка получения товара {product_id}: {response.status}")
                return []
            
            data = await response.json()
            if not data.get("success"):
                logger.warning(f"Неуспешный ответ для товара {product_id}")
                return []
            
            product_data = data["data"]
            images = []
            
            # Основное изображение
            picture = product_data.get("picture")
            if picture and picture.get("name"):
                images.append(create_image_object(product_id, product_code_1c, picture, "main"))
            
            # Дополнительные изображения
            for pic in product_data.get("pictures", []):
                if pic and pic.get("name"):
                    images.append(create_image_object(product_id, product_code_1c, pic, "additional"))
            
            if images:
                logger.info(f"Товар {product_id}: найдено {len(images)} изображений")
            
            return images
    
    try:
        return await retry_with_backoff(get_images)
    except Exception as e:
        logger.error(f"Ошибка запроса товара {product_id}: {e}")
        return []

async def process_batch(token: str, products_batch: List[Dict[str, str]], batch_num: int, config: Dict[str, str]) -> int:
    """Обработка партии товаров"""
    logger.info(f"Обработка партии {batch_num}: {len(products_batch)} товаров")
    
    timeout = aiohttp.ClientTimeout(total=Config.RETRY_TIMEOUT, connect=Config.RETRY_CONNECT_TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [get_product_images(session, token, product, config) for product in products_batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_images = []
        for result in results:
            if isinstance(result, list):
                all_images.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Ошибка обработки: {result}")
        
        if not all_images:
            return 0
        
        # Сохранение в Supabase
        supabase = get_supabase_client()
        saved_count = 0
        
        # Сохраняем партиями по 100 записей с upsert
        for i in range(0, len(all_images), Config.BATCH_SIZE):
            try:
                batch_slice = all_images[i:i + Config.BATCH_SIZE]
                result = supabase.table("product_images").upsert(
                    batch_slice, 
                    on_conflict="product_id,image_name"
                ).execute()
                saved_count += len(result.data) if result.data else 0
            except Exception as e:
                logger.error(f"Ошибка при сохранении части изображений: {e}")
                continue
        
        logger.info(f"Партия {batch_num}: сохранено {saved_count} изображений")
        return saved_count

async def main(batch_size: int = 20, max_products: Optional[int] = None, max_concurrent: int = 3) -> None:
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
            batch = products[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            async def process_batch_with_limit(batch_data, batch_number):
                async with semaphore:
                    result = await process_batch(token, batch_data, batch_number, config)
                    await asyncio.sleep(Config.RETRY_DELAY)
                    return result
            
            tasks.append(process_batch_with_limit(batch, batch_num))
        
        # Выполнение всех задач
        results = await asyncio.gather(*tasks)
        total_saved = sum(results)
        
        logger.info(f"Завершено! Обработано {len(products)} товаров, сохранено {total_saved} изображений")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Получение данных об изображениях товаров")
    parser.add_argument("--batch-size", type=int, default=20, help="Размер партии товаров")
    parser.add_argument("--max-products", type=int, default=None, help="Максимальное количество товаров")
    parser.add_argument("--max-concurrent", type=int, default=3, help="Максимальное количество одновременных партий")
    args = parser.parse_args()
    
    asyncio.run(main(
        batch_size=args.batch_size, 
        max_products=args.max_products, 
        max_concurrent=args.max_concurrent
    ))