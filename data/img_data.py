import os
import asyncio
import aiohttp
import argparse
import time
from dotenv import load_dotenv
from supabase import create_client
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
PIM_API_URL = os.getenv("PIM_API_URL")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Инициализация Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def retry_with_backoff(func, max_retries=3, initial_delay=1):
    """Retry функция с экспоненциальной задержкой"""
    for attempt in range(max_retries):
        try:
            return await func()
        except (aiohttp.ClientError, aiohttp.ServerTimeoutError, asyncio.TimeoutError) as e:
            if attempt == max_retries - 1:
                raise e
            delay = initial_delay * (2 ** attempt)
            logger.warning(f"Попытка {attempt + 1} не удалась, повтор через {delay}с: {e}")
            await asyncio.sleep(delay)
    return None

async def authorize_pim():
    """Авторизация в PIM API"""
    auth_url = f"{PIM_API_URL}/sign-in/"
    payload = {"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
    
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    
    async def _auth_request():
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(auth_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        return data["data"]["access"]["token"]
                raise Exception(f"Ошибка авторизации: {response.status}")
    
    return await retry_with_backoff(_auth_request)

def get_products_from_supabase(max_products=None):
    """Получение списка товаров из Supabase"""
    # Получаем данные из product_images вместо product_backup
    query = supabase.table('product_images').select('product_id, product_code_1c')
    if max_products:
        # Получаем больше записей, так как будем фильтровать дубликаты
        query = query.limit(max_products * 2)
    
    response = query.execute()
    if response.data:
        # Используем словарь для удаления дубликатов по product_id
        unique_products = {}
        for item in response.data:
            product_id = item.get("product_id")
            if product_id and product_id not in unique_products:
                unique_products[product_id] = {
                    "id": product_id,
                    "code_1c": item.get("product_code_1c", "")
                }
        
        # Преобразуем словарь в список
        products = list(unique_products.values())
        
        # Ограничиваем количество, если нужно
        if max_products and len(products) > max_products:
            products = products[:max_products]
            
        logger.info(f"Получено {len(products)} товаров из Supabase")
        return products
    
    logger.warning("Товары не найдены в Supabase")
    return []

async def get_product_images(session, token, product):
    """Получение изображений товара из PIM API"""
    product_id = product['id']
    product_code_1c = product.get('code_1c', '')
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{PIM_API_URL}/product/{product_id}"
    
    async def _get_images():
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
            base_url = "https://pim.uroven.pro/pictures/originals/"
            
            # Основное изображение
            picture = product_data.get("picture")
            if picture and picture.get("name"):
                # Обработка типа изображения с корректным извлечением расширения
                img_type = picture.get("type", "JPG")
                # Обработка различных форматов типа (например, "image/jpeg" или "JPEG")
                if img_type:
                    if "/" in img_type:
                        # Обработка MIME-типа (например, "image/jpeg")
                        ext = img_type.split("/")[-1].upper()
                    else:
                        # Обработка обычного типа (например, "JPEG" или "PNG")
                        ext = img_type.upper()
                else:
                    ext = "JPG"
                images.append({
                    "product_id": product_id,
                    "product_code_1c": product_code_1c,
                    "image_name": f"{picture['name']}.{ext}",
                    "image_url": f"{base_url}{picture['name']}.{ext}",
                    "image_type": "main",
                    "picture_id": picture.get("id"),
                    "is_downloaded": False,
                    "is_optimized": False,
                    "is_uploaded": False,
                    "optimized_url": None
                })
            
            # Дополнительные изображения
            for pic in product_data.get("pictures", []):
                if pic and pic.get("name"):
                    # Обработка типа изображения с корректным извлечением расширения
                    img_type = pic.get("type", "JPG")
                    # Обработка различных форматов типа (например, "image/jpeg" или "JPEG")
                    if img_type:
                        if "/" in img_type:
                            # Обработка MIME-типа (например, "image/jpeg")
                            ext = img_type.split("/")[-1].upper()
                        else:
                            # Обработка обычного типа (например, "JPEG" или "PNG")
                            ext = img_type.upper()
                    else:
                        ext = "JPG"
                    images.append({
                        "product_id": product_id,
                        "product_code_1c": product_code_1c,
                        "image_name": f"{pic['name']}.{ext}",
                        "image_url": f"{base_url}{pic['name']}.{ext}",
                        "image_type": "additional",
                        "picture_id": pic.get("id"),
                        "is_downloaded": False,
                        "is_optimized": False,
                        "is_uploaded": False,
                        "optimized_url": None
                    })
            
            if images:
                logger.info(f"Товар {product_id}: найдено {len(images)} изображений")
            
            return images
    
    try:
        return await retry_with_backoff(_get_images)
    except Exception as e:
        logger.error(f"Ошибка запроса товара {product_id}: {e}")
        return []

async def process_batch(token, products_batch, batch_num):
    """Обработка партии товаров"""
    logger.info(f"Обработка партии {batch_num}: {len(products_batch)} товаров")
    
    timeout = aiohttp.ClientTimeout(total=60, connect=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [get_product_images(session, token, product) for product in products_batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_images = []
        for result in results:
            if isinstance(result, list):
                all_images.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Ошибка обработки: {result}")
        
        # Сохранение в Supabase
        if all_images:
            try:
                # Сохраняем партиями по 100 записей с upsert
                saved_count = 0
                for i in range(0, len(all_images), 100):
                    try:
                        batch_slice = all_images[i:i + 100]
                        # Используем upsert с on_conflict для правильной обработки дубликатов
                        result = supabase.table("product_images").upsert(
                            batch_slice, 
                            on_conflict="product_id,image_name"
                        ).execute()
                        saved_count += len(result.data) if result.data else 0
                    except Exception as e:
                        logger.error(f"Ошибка при сохранении части изображений: {e}")
                        # Продолжаем с следующей партией даже при ошибке
                        continue
                
                logger.info(f"Партия {batch_num}: сохранено {saved_count} изображений")
                return saved_count
            except Exception as e:
                logger.error(f"Ошибка сохранения партии {batch_num}: {e}")
        
        return 0

async def main(batch_size=20, max_products=None, max_concurrent=3):
    """Основная функция"""
    try:
        # Авторизация
        token = await authorize_pim()
        logger.info("Авторизация в PIM API успешна")
        
        # Получение товаров из Supabase
        products = get_products_from_supabase(max_products)
        if not products:
            return
        
        logger.info(f"Начинаем обработку {len(products)} товаров")
        
        # Обработка партиями
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []
        
        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            async def process_with_semaphore(b, bn):
                async with semaphore:
                    result = await process_batch(token, b, bn)
                    # Небольшая задержка между партиями
                    await asyncio.sleep(0.5)
                    return result
            
            tasks.append(process_with_semaphore(batch, batch_num))
        
        # Выполнение всех задач
        results = await asyncio.gather(*tasks)
        total_saved = sum(results)
        
        logger.info(f"Завершено! Обработано {len(products)} товаров, сохранено {total_saved} изображений")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")

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