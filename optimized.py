import aiohttp
import asyncio
import os
import base64
from datetime import datetime
import logging
from supabase import create_client
import time
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("image_optimizer.log"), logging.StreamHandler()]
)
logger = logging.getLogger()

# Конфигурация
PIM_API_URL = "https://pim.uroven.pro/api/v1"
PIM_LOGIN = os.getenv("PIM_LOGIN", "s.andrey")
PIM_PASSWORD = os.getenv("PIM_PASSWORD", "KZh-4g2-YFx-Jgm")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://supabase.uroven.pro")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIn0.4AiJtu9AAgqihOClCQBLGLI3ZrqOfcbyp6_035gGHr0")
IMGPROXY_URL = "https://images.uroven.pro"

# Инициализация Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Семафор для ограничения одновременных запросов
semaphore = asyncio.Semaphore(10)

async def get_auth_token(session):
    """Получение токена авторизации"""
    auth_data = {
        "login": PIM_LOGIN,
        "password": PIM_PASSWORD,
        "remember": True
    }
    try:
        async with session.post(f"{PIM_API_URL}/sign-in/", json=auth_data) as response:
            if response.status == 200:
                data = await response.json()
                if data["success"]:
                    return data["data"]["access"]["token"]
            logger.error(f"Ошибка авторизации: {await response.text()}")
            return None
    except Exception as e:
        logger.error(f"Ошибка при авторизации: {str(e)}")
        return None

async def get_product_details(session, token, product_id):
    """Получение информации о товаре по ID"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with semaphore, session.get(f"{PIM_API_URL}/product/{product_id}", headers=headers) as response:
            if response.status == 200:
                return await response.json()
            logger.warning(f"Не удалось получить данные товара {product_id}. Код: {response.status}")
            return None
    except Exception as e:
        logger.error(f"Ошибка при получении данных товара {product_id}: {str(e)}")
        return None


async def optimize_image_via_imgproxy(session, original_image_url):
    """Оптимизация изображения через imgproxy"""
    try:
        # Проверяем доступность исходного изображения
        async with session.head(original_image_url) as check_response:
            if check_response.status != 200:
                logger.warning(f"Исходное изображение недоступно: {original_image_url} (код: {check_response.status})")
                return None, None
        
        # Кодируем URL в Base64 для imgproxy
        b64_url = base64.urlsafe_b64encode(original_image_url.encode()).decode().rstrip("=")
        
        # Формируем imgproxy URL согласно документации:
        # unsafe - без подписи (т.к. безопасность отключена)
        # resize:fill:750:1000 - изменить размер до 750x1000 с заполнением
        # extend:1:ce - расширить с фоном по центру
        # quality:85 - качество 85%
        # .jpeg - выходной формат
        imgproxy_url = f"{IMGPROXY_URL}/unsafe/resize:fill:750:1000/extend:1:ce/quality:85/{b64_url}.jpeg"
        
        logger.info(f"Обработка через imgproxy: {imgproxy_url}")
        
        # Скачиваем обработанное изображение
        async with semaphore, session.get(imgproxy_url) as response:
            if response.status == 200:
                return await response.read(), imgproxy_url
            logger.warning(f"Ошибка imgproxy обработки. Код: {response.status}")
            if response.status == 404:
                logger.warning(f"Проверьте URL исходного изображения: {original_image_url}")
            return None, None
    except Exception as e:
        logger.error(f"Ошибка при обработке через imgproxy: {str(e)}")
        return None, None

async def upload_image_to_pim(session, token, product_id, image_data):
    """Загрузка изображения в PIM"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        form_data = aiohttp.FormData()
        form_data.add_field('file', image_data, 
                           filename=f'optimized_{datetime.now().strftime("%Y%m%d%H%M%S")}.jpg',
                           content_type='image/jpeg')
        
        async with semaphore, session.post(f"{PIM_API_URL}/product/{product_id}/upload-picture", 
                                headers=headers, data=form_data) as response:
            if response.status == 200:
                return await response.json()
            logger.warning(f"Не удалось загрузить изображение для товара {product_id}. Код: {response.status}")
            return None
    except Exception as e:
        logger.error(f"Ошибка при загрузке изображения для товара {product_id}: {str(e)}")
        return None

async def delete_image_from_pim(session, token, product_id, picture_id):
    """Удаление изображения из PIM"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with semaphore, session.delete(f"{PIM_API_URL}/product/{product_id}/picture/{picture_id}", 
                            headers=headers) as response:
            if response.status == 200:
                return await response.json()
            logger.warning(f"Не удалось удалить изображение {picture_id} товара {product_id}. Код: {response.status}")
            return None
    except Exception as e:
        logger.error(f"Ошибка при удалении изображения {picture_id} товара {product_id}: {str(e)}")
        return None

async def scan_product_images(session, token):
    """Сканирование всех товаров и сохранение информации об изображениях в БД"""
    logger.info("📋 Начало сканирования изображений товаров...")
    
    # Получаем список товаров из product_backup
    try:
        response = supabase.table('product_backup').select('id, code_1c').execute()
        products = response.data if response.data else []
        logger.info(f"Найдено {len(products)} товаров для сканирования")
    except Exception as e:
        logger.error(f"Ошибка при получении товаров: {str(e)}")
        return 0
    
    scanned_count = 0
    for product in products:
        product_id = product['id']
        code_1c = product.get('code_1c', '')
        
        # Получаем детали товара из PIM
        product_details = await get_product_details(session, token, product_id)
        if not product_details or not product_details.get("data"):
            continue
            
        product_data = product_details["data"]
        
        # Обработка основного изображения с дополнительными
        main_picture = product_data.get("picture")
        if main_picture and main_picture.get("name"):
            # Собираем дополнительные изображения
            additional_pictures = product_data.get("pictures", [])
            additional_urls = []
            additional_ids = []
            
            for pic in additional_pictures:
                if pic and pic.get("name"):
                    ext = pic.get("type", "JPG").split("/")[-1].upper() if pic.get("type") else "JPG"
                    additional_urls.append(f"https://pim.uroven.pro/pictures/originals/{pic['name']}.{ext}")
                    if pic.get("id"):
                        additional_ids.append(str(pic.get("id")))
            
            # Создаем одну запись с основным и дополнительными изображениями
            ext = main_picture.get("type", "JPG").split("/")[-1].upper() if main_picture.get("type") else "JPG"
            image_data = {
                'product_id': product_id,
                'product_code_1c': code_1c,
                'image_name': f"{main_picture['name']}.{ext}",
                'image_url': f"https://pim.uroven.pro/pictures/originals/{main_picture['name']}.{ext}",
                'image_type': 'main',
                'picture_id': str(main_picture.get("id", "")),
                'additional_image_urls': ",".join(additional_urls) if additional_urls else None,
                'additional_picture_ids': ",".join(additional_ids) if additional_ids else None
            }
            
            try:
                supabase.table('product_images').upsert(image_data).execute()
                scanned_count += 1
                logger.info(f"Товар {product_id}: основное изображение и {len(additional_urls)} дополнительных")
            except Exception as e:
                logger.error(f"Ошибка при сохранении изображения: {str(e)}")
    
    logger.info(f"Сканирование завершено. Найдено {scanned_count} изображений")
    return scanned_count

async def optimize_images(session, limit=None):
    """Оптимизация изображений через imgproxy"""
    logger.info("Начало оптимизации изображений...")
    
    # Получаем необработанные изображения
    query = supabase.table('product_images').select('*').eq('is_optimized', False)
    if limit:
        query = query.limit(limit)
        
    try:
        response = query.execute()
        images = response.data if response.data else []
        logger.info(f"Найдено {len(images)} изображений для оптимизации")
    except Exception as e:
        logger.error(f"Ошибка при получении изображений: {str(e)}")
        return 0
    
    optimized_count = 0
    for image in images:
        # Оптимизируем через imgproxy
        result = await optimize_image_via_imgproxy(session, image['image_url'])
        if result and result[0]:  # Проверяем что получили данные
            optimized_data, optimized_url = result
            # Сохраняем URL оптимизированного изображения
            try:
                supabase.table('product_images').update({
                    'is_optimized': True,
                    'optimized_url': optimized_url
                }).eq('id', image['id']).execute()
                
                optimized_count += 1
                logger.info(f"Оптимизировано: {image['image_name']} (Product ID: {image['product_id']})")
                
                # Для режима preview показываем ID товара
                if limit and limit <= 5:
                    logger.info(f"Product ID для проверки: {image['product_id']}")
                    
            except Exception as e:
                logger.error(f"Ошибка при обновлении статуса оптимизации: {str(e)}")
    
    logger.info(f"Оптимизация завершена. Обработано {optimized_count} изображений")
    return optimized_count

async def upload_optimized_images(session, token, limit=None):
    """Загрузка оптимизированных изображений в PIM"""
    logger.info("Начало загрузки оптимизированных изображений...")
    
    # Получаем оптимизированные но незагруженные изображения
    query = supabase.table('product_images').select('*').eq('is_optimized', True).eq('is_uploaded', False)
    if limit:
        query = query.limit(limit)
        
    try:
        response = query.execute()
        images = response.data if response.data else []
        logger.info(f"Найдено {len(images)} изображений для загрузки")
    except Exception as e:
        logger.error(f"Ошибка при получении изображений: {str(e)}")
        return 0
    
    uploaded_count = 0
    for image in images:
        # Скачиваем оптимизированное изображение
        result = await optimize_image_via_imgproxy(session, image['image_url'])
        if result and result[0]:
            optimized_data, _ = result
            # Загружаем в PIM
            upload_result = await upload_image_to_pim(session, token, image['product_id'], optimized_data)
            if upload_result and upload_result.get("success"):
                # Удаляем старое изображение если есть picture_id
                if image['picture_id']:
                    await delete_image_from_pim(session, token, image['product_id'], image['picture_id'])
                
                # Обновляем статус
                try:
                    supabase.table('product_images').update({
                        'is_uploaded': True,
                        'updated_at': datetime.now().isoformat()
                    }).eq('id', image['id']).execute()
                    
                    uploaded_count += 1
                    logger.info(f"Загружено: {image['image_name']} (Product ID: {image['product_id']})")
                    
                except Exception as e:
                    logger.error(f"Ошибка при обновлении статуса загрузки: {str(e)}")
    
    logger.info(f"Загрузка завершена. Загружено {uploaded_count} изображений")
    return uploaded_count

async def clean_unavailable_images(session, limit=None):
    """Очистка недоступных изображений из базы данных"""
    logger.info("Очистка недоступных изображений...")
    
    try:
        query = supabase.table('product_images').select('id, image_url')
        if limit:
            query = query.limit(limit)
        response = query.execute()
        images = response.data if response.data else []
        
        if limit:
            logger.info(f"Быстрая проверка первых {len(images)} изображений...")
        else:
            logger.info(f"Полная проверка {len(images)} изображений...")
        
        removed_count = 0
        for i, image in enumerate(images):
            if i % 10 == 0:  # Показываем прогресс каждые 10 изображений
                logger.info(f"Проверено {i}/{len(images)} изображений...")
                
            try:
                async with session.head(image['image_url']) as check_response:
                    if check_response.status != 200:
                        # Удаляем недоступное изображение
                        supabase.table('product_images').delete().eq('id', image['id']).execute()
                        removed_count += 1
                        if removed_count <= 10:  # Логируем только первые 10 удалений
                            logger.info(f"Удалено недоступное: {image['image_url']}")
            except Exception:
                # Если ошибка при проверке - тоже удаляем
                supabase.table('product_images').delete().eq('id', image['id']).execute()
                removed_count += 1
        
        logger.info(f"Очистка завершена. Удалено {removed_count} недоступных изображений")
        return removed_count
    except Exception as e:
        logger.error(f"Ошибка при очистке: {str(e)}")
        return 0

async def preview_images(session, token):
    """Режим предпросмотра - обработка 1-5 изображений для проверки"""
    logger.info("РЕЖИМ ПРЕДПРОСМОТРА - обработка 1-5 изображений")
    
    # Быстрая очистка для preview (только первые 20 записей)
    await clean_unavailable_images(session, limit=20)
    
    # Сканируем первые несколько товаров для получения актуальных изображений
    try:
        response = supabase.table('product_backup').select('id, code_1c').limit(5).execute()
        products = response.data if response.data else []
    except Exception as e:
        logger.error(f"Ошибка при получении товаров: {str(e)}")
        return
    
    # Быстрое сканирование первых товаров
    scanned_count = 0
    for product in products:
        product_id = product['id']
        product_details = await get_product_details(session, token, product_id)
        if product_details and product_details.get("data"):
            product_data = product_details["data"]
            
            # Сканируем только основное изображение для preview
            main_picture = product_data.get("picture")
            if main_picture and main_picture.get("name"):
                image_url = f"https://pim.uroven.pro/pictures/originals/{main_picture['name']}.JPG"
                
                # Проверяем доступность изображения
                try:
                    async with session.head(image_url) as check_response:
                        if check_response.status == 200:
                            image_data = {
                                'product_id': product_id,
                                'product_code_1c': product.get('code_1c', ''),
                                'image_name': main_picture["name"] + ".JPG",
                                'image_url': image_url,
                                'image_type': 'main',
                                'picture_id': str(main_picture.get("id", "")),
                                'additional_image_urls': None,
                                'additional_picture_ids': None
                            }
                            supabase.table('product_images').upsert(image_data).execute()
                            scanned_count += 1
                            logger.info(f"Найдено доступное изображение для товара {product_id}")
                            
                            if scanned_count >= 3:  # Достаточно для preview
                                break
                except Exception:
                    continue
    
    logger.info(f"Найдено {scanned_count} доступных изображений")
    
    # Оптимизируем найденные изображения
    await optimize_images(session, limit=5)
    
    logger.info("\nПредпросмотр завершен! Проверьте указанные Product ID в PIM")

async def main(mode='full'):
    """Основная функция программы
    
    Режимы работы:
    - scan: только сканирование изображений
    - optimize: только оптимизация 
    - upload: только загрузка
    - preview: тестовый режим (1-5 изображений)
    - clean: очистка недоступных изображений
    - full: полный цикл (по умолчанию)
    """
    logger.info(f"Запуск в режиме: {mode.upper()}")
    
    async with aiohttp.ClientSession() as session:
        # Режим очистки не требует авторизации
        if mode == 'clean':
            await clean_unavailable_images(session)  # Полная очистка без ограничений
            return
        
        # Получаем токен авторизации для других режимов
        token = await get_auth_token(session)
        if not token:
            logger.error("Ошибка авторизации. Проверьте логин и пароль.")
            return
        
        if mode == 'preview':
            await preview_images(session, token)
            return
        
        if mode in ['scan', 'full']:
            await scan_product_images(session, token)
        
        if mode in ['optimize', 'full']:
            await optimize_images(session)
        
        if mode in ['upload', 'full']:
            await upload_optimized_images(session, token)
        
        logger.info("Процесс завершен!")

async def test_imgproxy():
    """Тестирование imgproxy с примером изображения"""
    test_url = "https://pim.uroven.pro/pictures/originals/test.JPG"
    async with aiohttp.ClientSession() as session:
        result = await optimize_image_via_imgproxy(session, test_url)
        if result and result[0]:
            logger.info("Тест imgproxy прошел успешно")
            logger.info(f"Размер оптимизированного изображения: {len(result[0])} байт")
            return True
        else:
            logger.error("Тест imgproxy провалился")
            return False

if __name__ == "__main__":
    start_time = time.time()
    
    # Определяем режим работы из аргументов командной строки
    mode = 'full'
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode not in ['scan', 'optimize', 'upload', 'preview', 'clean', 'full', 'test']:
            logger.error(f"❌ Неизвестный режим: {mode}")
            logger.info("Доступные режимы:")
            logger.info("  python optimized.py scan      - сканирование изображений")
            logger.info("  python optimized.py optimize  - оптимизация изображений") 
            logger.info("  python optimized.py upload    - загрузка в PIM")
            logger.info("  python optimized.py preview   - тестовый режим (1-5 изображений)")
            logger.info("  python optimized.py clean     - очистка недоступных изображений")
            logger.info("  python optimized.py full      - полный цикл (по умолчанию)")
            logger.info("  python optimized.py test      - тест imgproxy")
            sys.exit(1)
    
    try:
        if mode == 'test':
            asyncio.run(test_imgproxy())
        else:
            asyncio.run(main(mode))
        logger.info(f"Общее время выполнения: {time.time() - start_time:.2f} сек.")
    except KeyboardInterrupt:
        logger.info("Процесс прерван пользователем")
    except Exception as e:
        logger.error(f"Ошибка в основном процессе: {str(e)}")
        sys.exit(1)