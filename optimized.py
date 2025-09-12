import aiohttp
import asyncio
import os
import base64
import logging
from datetime import datetime
from supabase import create_client

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger()

# Конфигурация
PIM_API_URL = os.getenv("PIM_API_URL")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
IMGPROXY_URL = "https://images.uroven.pro"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def get_auth_token(session):
    """Получение токена авторизации PIM"""
    auth_data = {"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
    async with session.post(f"{PIM_API_URL}/sign-in/", json=auth_data) as response:
        if response.status == 200:
            data = await response.json()
            if data["success"]:
                return data["data"]["access"]["token"]
    logger.error("Ошибка авторизации")
    return None

async def optimize_image(session, image_url):
    """Оптимизация изображения через imgproxy"""
    try:
        # Проверяем доступность исходного изображения
        async with session.head(image_url) as check:
            if check.status != 200:
                return None, None
        
        # Кодируем URL для imgproxy
        b64_url = base64.urlsafe_b64encode(image_url.encode()).decode().rstrip("=")
        imgproxy_url = f"{IMGPROXY_URL}/unsafe/resize:fill:750:1000/extend:1:ce/quality:85/{b64_url}.jpeg"
        
        # Получаем оптимизированное изображение
        async with session.get(imgproxy_url) as response:
            if response.status == 200:
                return await response.read(), imgproxy_url
        return None, None
    except Exception as e:
        logger.error(f"Ошибка оптимизации: {e}")
        return None, None

async def upload_to_pim(session, token, product_id, image_data):
    """Загрузка изображения в PIM"""
    headers = {"Authorization": f"Bearer {token}"}
    form_data = aiohttp.FormData()
    form_data.add_field('file', image_data, 
                       filename=f'opt_{datetime.now().strftime("%Y%m%d%H%M%S")}.jpg',
                       content_type='image/jpeg')
    
    try:
        async with session.post(f"{PIM_API_URL}/product/{product_id}/upload-picture", 
                               headers=headers, data=form_data) as response:
            return response.status == 200
    except Exception as e:
        logger.error(f"Ошибка загрузки: {e}")
        return False

async def delete_from_pim(session, token, product_id, picture_id):
    """Удаление изображения из PIM"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with session.delete(f"{PIM_API_URL}/product/{product_id}/picture/{picture_id}", 
                                 headers=headers) as response:
            return response.status == 200
    except Exception as e:
        logger.error(f"Ошибка удаления: {e}")
        return False

async def process_image(session, token, image_record):
    """Обработка одного изображения: оптимизация -> загрузка -> удаление старого"""
    image_id = image_record['id']
    product_id = image_record['product_id']
    image_url = image_record['image_url']
    picture_id = image_record.get('picture_id')
    
    logger.info(f"Обработка изображения {image_record['image_name']} (Product: {product_id})")
    
    # 1. Оптимизируем
    optimized_data, optimized_url = await optimize_image(session, image_url)
    if not optimized_data:
        logger.warning(f"Не удалось оптимизировать изображение {image_id}")
        return False
    
    # 2. Загружаем в PIM
    if not await upload_to_pim(session, token, product_id, optimized_data):
        logger.warning(f"Не удалось загрузить изображение {image_id}")
        return False
    
    # 3. Удаляем старое из PIM (если есть picture_id)
    if picture_id:
        await delete_from_pim(session, token, product_id, picture_id)
    
    # 4. Обновляем статус в БД
    try:
        supabase.table('product_images').update({
            'is_optimized': True,
            'is_uploaded': True,
            'optimized_url': optimized_url,
            'updated_at': datetime.now().isoformat()
        }).eq('id', image_id).execute()
        
        logger.info(f"✅ Успешно обработано изображение {image_record['image_name']}")
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления БД: {e}")
        return False

async def main(limit=None):
    """Основная функция - оптимизация изображений из БД"""
    logger.info("🚀 Запуск оптимизации изображений")
    
    # Получаем неоптимизированные изображения
    query = supabase.table('product_images').select('*').eq('is_optimized', False)
    if limit:
        query = query.limit(limit)
    
    try:
        response = query.execute()
        images = response.data or []
        logger.info(f"Найдено {len(images)} изображений для обработки")
    except Exception as e:
        logger.error(f"Ошибка получения изображений: {e}")
        return
    
    if not images:
        logger.info("Нет изображений для обработки")
        return
    
    async with aiohttp.ClientSession() as session:
        # Авторизация
        token = await get_auth_token(session)
        if not token:
            logger.error("Не удалось получить токен авторизации")
            return
        
        logger.info("✅ Авторизация успешна")
        
        # Обработка изображений
        success_count = 0
        semaphore = asyncio.Semaphore(5)  # Ограничиваем до 5 одновременных запросов
        
        async def process_with_limit(image):
            async with semaphore:
                return await process_image(session, token, image)
        
        # Обрабатываем параллельно
        tasks = [process_with_limit(image) for image in images]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Подсчитываем успешные
        for result in results:
            if result is True:
                success_count += 1
        
        logger.info(f"🎉 Завершено! Успешно обработано: {success_count}/{len(images)} изображений")

if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else None
    if limit:
        logger.info(f"Режим тестирования: обработка {limit} изображений")
    asyncio.run(main(limit))