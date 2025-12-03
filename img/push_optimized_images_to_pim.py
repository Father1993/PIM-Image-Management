import os
import asyncio
import aiohttp
import json
import signal
import time
from supabase import create_client
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

load_dotenv()


PIM_API_URL = os.getenv("PIM_API_URL")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

PROGRESS_FILE = "upload_progress.json"


class TokenManager:
    """Менеджер токенов с автоматическим обновлением"""
    def __init__(self, session):
        self.session = session
        self.token = None
        self.token_expires = 0
        self.refresh_interval = 3600  # 1 час в секундах
    
    async def get_valid_token(self):
        """Получить валидный токен, обновляя при необходимости"""
        current_time = time.time()
        
        if not self.token or current_time >= self.token_expires:
            logger.info("🔄 Обновляем токен авторизации...")
            self.token = await get_pim_token(self.session)
            if self.token:
                self.token_expires = current_time + self.refresh_interval
                logger.info("✅ Токен обновлен успешно")
            else:
                logger.error("❌ Не удалось обновить токен")
                return None
        
        return self.token


def save_progress(completed_ids):
    """Сохранить прогресс в файл"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(list(completed_ids), f)


def load_progress():
    """Загрузить прогресс из файла"""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r') as f:
                data = json.load(f)
                return set(data) if data else set()
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Файл прогресса {PROGRESS_FILE} поврежден, начинаем заново")
            clear_progress()
    return set()


def clear_progress():
    """Очистить файл прогресса"""
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)


async def get_pim_token(session):
    """Получить токен авторизации PIM API"""
    login_data = {"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
    try:
        async with session.post(f"{PIM_API_URL}/api/v1/sign-in/", json=login_data) as response:
            data = await response.json()
            if data.get("success") and data.get("data", {}).get("access", {}).get("token"):
                logger.info(f"Токен получен: {data['data']['access']['token']}")
                return data["data"]["access"]["token"]
            else:
                logger.error(f"Не удалось получить токен: {data}")
    except Exception as e:
        logger.error(f"Ошибка получения токена: {e}")
    return None





async def upload_image_to_pim(session, product_id, image_url, token_manager, semaphore, completed_count, total):
    """Скачать изображение по URL и загрузить в PIM"""
    async with semaphore:  # Ограничиваем количество одновременных запросов
        token = await token_manager.get_valid_token()
        if not token:
            logger.error(f"Не удалось получить токен для товара {product_id}")
            return None
            
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{PIM_API_URL}/api/v1/product/{product_id}/upload-main-picture"
        
        try:
            # 1. Скачиваем изображение
            async with session.get(image_url) as resp:
                if resp.status != 200:
                    logger.error(f"Не удалось скачать изображение {image_url}: {resp.status}")
                    return None
                image_bytes = await resp.read()

            # 2. Формируем form-data
            form = aiohttp.FormData()
            form.add_field(
                name="file",
                value=image_bytes,
                filename=os.path.basename(image_url),
                content_type="image/jpeg"  
            )

            # 3. Отправляем POST запрос в PIM
            async with session.post(url, headers=headers, data=form) as response:
                text = await response.text()
                if response.status != 200:
                    logger.error(f"Ошибка загрузки товара {product_id} ({response.status}): {text}")
                    return None
                
                current = completed_count[0] + 1
                completed_count[0] = current
                progress = (current / total) * 100
                logger.info(f"[{current}/{total}] ({progress:.1f}%) ✅ Успешно загружено для товара {product_id}")
                return product_id
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке товара {product_id}: {e}")
            return None



    

async def main():
    # Загружаем прогресс
    completed_ids = load_progress()
    if completed_ids:
        logger.info(f"📋 Найден прогресс: {len(completed_ids)} товаров уже обработано")
    
    # Подключение к Supabase
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Определяем название таблицы
    table_name = "products"

    test = client.table(table_name).select("id").limit(1).execute()
    table_found = table_name
    if not table_found:
        logger.error("Таблица не найдена! Проверьте название таблицы в Supabase")
        return
    logger.info(f"Найдена таблица: {table_name}")
    response = client.table(table_name).select("id, image_optimized_url").execute()

    all_ids = [item["id"] for item in response.data]
    all_images = [item["image_optimized_url"] for item in response.data]
    
    # Фильтруем уже обработанные товары
    remaining_data = [(id, img) for id, img in zip(all_ids, all_images) if id not in completed_ids]
    
    if not remaining_data:
        logger.info("🎉 Все товары уже обработаны!")
        clear_progress()
        return
    
    total_items = len(all_ids)
    remaining_count = len(remaining_data)
    logger.info(f"📊 Всего товаров: {total_items}, осталось: {remaining_count}")
    logger.info(f"🚀 Начинаем загрузку {remaining_count} изображений...")
    
    # Глобальная переменная для доступа к прогрессу из обработчика сигналов
    global_progress = {
        "completed_ids": completed_ids, 
        "total_items": total_items,
        "current_batch_results": [],
        "current_batch_tasks": []
    }
    
    # Обработчик для корректной остановки
    def signal_handler(signum, frame):
        logger.info("\n⏹️ Получен сигнал остановки. Сохраняем прогресс...")
        
        # Сохраняем результаты текущего незавершенного батча
        current_completed = set(global_progress["completed_ids"])
        for result in global_progress["current_batch_results"]:
            if result and not isinstance(result, Exception):
                current_completed.add(result)
        
        save_progress(list(current_completed))
        logger.info(f"💾 Прогресс сохранен. Обработано: {len(current_completed)}/{global_progress['total_items']}")
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    async with aiohttp.ClientSession() as session:
        # Создаем менеджер токенов
        token_manager = TokenManager(session)
        
        # Получаем первый токен
        token = await token_manager.get_valid_token()
        if not token:
            logger.error("Не удалось получить токен авторизации PIM API")
            return
        
        # Создаем семафор для ограничения одновременных запросов (100)
        semaphore = asyncio.Semaphore(100)
        completed_count = [len(completed_ids)]  # Используем список для изменения в async функциях
        
        try:
            # Создаем задачи для всех товаров
            tasks = []
            for product_id, image_url in remaining_data:
                task = upload_image_to_pim(session, product_id, image_url, token_manager, semaphore, completed_count, total_items)
                tasks.append(task)
            
            # Запускаем все задачи параллельно
            logger.info(f"🚀 Запускаем {len(tasks)} задач параллельно (макс. 100 одновременно)...")
            
            # Запускаем задачи батчами для периодического сохранения прогресса
            batch_size = 1000  # Сохраняем прогресс каждые 100 задач (чаще!)
            results = []
            
            for i in range(0, len(tasks), batch_size):
                batch_tasks = tasks[i:i + batch_size]
                logger.info(f"📦 Обрабатываем батч {i//batch_size + 1}: задачи {i+1}-{min(i+batch_size, len(tasks))}")
                
                # Обновляем глобальный прогресс для отслеживания текущего батча
                global_progress["current_batch_tasks"] = batch_tasks
                global_progress["current_batch_results"] = []
                
                # Обрабатываем задачи по мере их завершения
                batch_results = []
                for task in asyncio.as_completed(batch_tasks):
                    try:
                        result = await task
                        batch_results.append(result)
                        
                        # Обновляем прогресс в реальном времени
                        if result and not isinstance(result, Exception):
                            completed_ids.add(result)
                            global_progress["completed_ids"].add(result)
                        
                        # Обновляем результаты текущего батча
                        global_progress["current_batch_results"] = batch_results
                        
                    except Exception as e:
                        batch_results.append(e)
                        global_progress["current_batch_results"] = batch_results
                
                results.extend(batch_results)
                
                # Сохраняем прогресс после каждого батча
                current_completed = len(completed_ids)
                save_progress(list(completed_ids))
                logger.info(f"💾 Прогресс сохранен: {current_completed} товаров обработано")
            
            # Финальная обработка результатов
            success_count = len(completed_ids)
            
            # Завершение
            clear_progress()
            logger.info(f"🎉 Завершено! Успешно загружено: {success_count}/{total_items} изображений")
            
        except KeyboardInterrupt:
            logger.info("\n⏹️ Остановка по Ctrl+C...")
            
            # Сохраняем результаты текущего незавершенного батча
            current_completed = set(global_progress["completed_ids"])
            for result in global_progress["current_batch_results"]:
                if result and not isinstance(result, Exception):
                    current_completed.add(result)
            
            save_progress(list(current_completed))
            logger.info(f"💾 Прогресс сохранен. Обработано: {len(current_completed)}/{global_progress['total_items']}")
            return
        

            

if __name__ == "__main__":
    asyncio.run(main())
