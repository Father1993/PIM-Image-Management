#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для выгрузки всех товаров из каталога ID 21 из Compo PIM API
с использованием scroll метода и httpx для асинхронных запросов
Сохраняет все товары в JSON файл

ОПТИМИЗАЦИИ:
- Использует библиотеку httpx вместо requests для ускорения работы
- Асинхронная обработка запросов для повышения скорости загрузки
- Включен HTTP/2 для повышения эффективности запросов
- Настроены лимиты подключений для оптимальной производительности
- Переиспользование соединений через контекстные менеджеры
- Сохранение промежуточных результатов при ошибках соединения
- Автоматическое сохранение данных при отсутствии scroll_id

ТРЕБОВАНИЯ:
- Python 3.7+ (требуется для использования asyncio)
- httpx
- dotenv

УСТАНОВКА:
pip install httpx python-dotenv
"""

import os
import json
import asyncio
import httpx
import time
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Конфигурация
PIM_API_URL = os.getenv("PIM_API_URL", "https://pim.uroven.pro/api/v1")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")

# ID каталога
CATALOG_ID = 21  # Каталог ID 21

# Настройки httpx клиента
HTTPX_TIMEOUT = 60.0  # Таймаут для запросов в секундах
# Лимиты соединений: 
# - max_keepalive_connections: максимальное количество соединений, которые будут держаться открытыми
# - max_connections: максимальное общее количество соединений
HTTPX_LIMITS = httpx.Limits(max_keepalive_connections=10, max_connections=20)

# Настройки для повторных попыток
MAX_RETRIES = 3
RETRY_DELAY = 5  # секунд между повторными попытками


async def authenticate():
    """
    Асинхронная авторизация в PIM API и получение токена
    
    Returns:
        str: Токен авторизации для API запросов
    
    Raises:
        httpx.HTTPStatusError: При ошибке HTTP статуса в запросе
        httpx.RequestError: При проблемах с подключением
        Exception: При ошибке в ответе API
    """
    print("[🔐] Авторизация в PIM API...")
    
    # Используем AsyncClient для асинхронных запросов
    # http2=True включает поддержку HTTP/2 (значительно повышает скорость для множественных запросов)
    # limits устанавливает ограничения на количество одновременных соединений
    async with httpx.AsyncClient(
        timeout=HTTPX_TIMEOUT,
        http2=True,
        limits=HTTPX_LIMITS
    ) as client:
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.post(
                    f"{PIM_API_URL}/sign-in/",
                    json={
                        "login": PIM_LOGIN, 
                        "password": PIM_PASSWORD, 
                        "remember": True
                    }
                )
                
                # Проверяем HTTP статус ответа
                response.raise_for_status()
                data = response.json()
                
                if data.get("success"):
                    print("[✅] Авторизация успешна")
                    return data["data"]["access"]["token"]
                else:
                    raise Exception(f"[❌] Ошибка авторизации: {data}")
            
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"[⚠️] Ошибка при авторизации (попытка {attempt+1}/{MAX_RETRIES}): {e}")
                    print(f"[🕒] Ожидание {RETRY_DELAY} секунд перед повторной попыткой...")
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    print(f"[❌] Все попытки авторизации не удались: {e}")
                    raise


async def fetch_catalog21_products(token):
    """
    Асинхронное получение всех товаров из каталога ID 21 с использованием scroll API
    
    Args:
        token (str): Токен авторизации
    
    Returns:
        list: Список словарей с информацией о товарах
    
    Raises:
        httpx.HTTPStatusError: При ошибке HTTP статуса в запросе
        httpx.RequestError: При проблемах с подключением
        Exception: При ошибке в ответе API
    """
    print(f"[🔄] Начинаем загрузку всех товаров из каталога ID {CATALOG_ID}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    all_products = []
    scroll_id = None
    total_fetched = 0
    batch_num = 0
    empty_responses_in_row = 0  # Счетчик пустых ответов подряд
    PAUSE_AFTER_BATCHES = 255  # Пауза после каждых N запросов
    PAUSE_DURATION = 10  # Длительность паузы в секундах
    
    # Инициализируем один HTTP клиент для всех запросов
    # Это позволяет переиспользовать соединения вместо создания нового для каждого запроса
    async with httpx.AsyncClient(
        headers=headers,
        timeout=HTTPX_TIMEOUT,
        http2=True,
        limits=HTTPX_LIMITS
    ) as client:
        while True:
            batch_num += 1
            print(f"[📥] Загрузка партии #{batch_num}...", end="", flush=True)
            
            # Пауза каждые N запросов для предотвращения ConnectionTerminated
            if batch_num > PAUSE_AFTER_BATCHES and (batch_num - 1) % PAUSE_AFTER_BATCHES == 0:
                print(f"\n[⏸️] Пауза {PAUSE_DURATION} секунд после {PAUSE_AFTER_BATCHES} запросов...")
                await asyncio.sleep(PAUSE_DURATION)
                print(f"[▶️] Продолжаем загрузку...")
            
            try:
                # Выполняем асинхронный GET-запрос с повторными попытками
                # URL формируем внутри цикла, чтобы использовать актуальный scroll_id
                for attempt in range(MAX_RETRIES):
                    try:
                        # Формируем URL в зависимости от наличия scroll_id
                        if scroll_id:
                            url = f"{PIM_API_URL}/product/scroll?catalogId={CATALOG_ID}&scrollId={scroll_id}"
                        else:
                            # Начальный запрос для каталога ID 21 без scroll_id
                            url = f"{PIM_API_URL}/product/scroll?catalogId={CATALOG_ID}"
                        
                        response = await client.get(url)
                        break  # Если запрос успешен, выходим из цикла повторных попыток
                    except (httpx.RequestError, httpx.HTTPStatusError) as e:
                        if attempt < MAX_RETRIES - 1:
                            print(f"\n[⚠️] Ошибка при запросе (попытка {attempt+1}/{MAX_RETRIES}): {e}")
                            print(f"[🕒] Ожидание {RETRY_DELAY} секунд перед повторной попыткой...")
                            await asyncio.sleep(RETRY_DELAY)
                        else:
                            print(f"\n[❌] Все попытки запроса не удались: {e}")
                            # Сохраняем то, что успели получить
                            print(f"\n[⚠️] Прерываем загрузку. Сохраняем {len(all_products)} полученных товаров.")
                            return all_products
                
                # Проверяем ответ
                if response.status_code != 200:
                    print(f"\n[❌] Ошибка запроса: {response.status_code}")
                    # Сохраняем то, что уже получили
                    return all_products
                    
                data = response.json()
                
                if not data.get("success"):
                    print(f"\n[❌] Ошибка в ответе API: {data}")
                    # Сохраняем то, что уже получили
                    return all_products
                
                # Извлекаем данные
                response_data = data.get("data", {})
                products = response_data.get("products", [])  # Основное поле с товарами
                new_scroll_id = response_data.get("scrollId")
                total = response_data.get("total", 0)  # Общее количество товаров
                
                # Если вдруг используется другое поле (как в некоторых скриптах)
                if not products:
                    products = response_data.get("productElasticDtos", [])
                
                if products:
                    all_products.extend(products)
                    count = len(products)
                    total_fetched += count
                    empty_responses_in_row = 0  # Сбрасываем счетчик при успешном ответе
                    print(f" [✅] Получено {count} товаров (всего: {total_fetched}" + 
                          (f" из {total})" if total > 0 else ")"))
                    scroll_id = new_scroll_id
                else:
                    empty_responses_in_row += 1
                    # Если 3 пустых ответа подряд - прекращаем (защита от бесконечного цикла)
                    if empty_responses_in_row >= 3:
                        print(f" [⚠️] Получено {empty_responses_in_row} пустых ответов подряд. Завершаем.")
                        if total > 0 and total_fetched < total:
                            print(f" [⚠️] Загружено {total_fetched} из {total}. Возможна потеря данных.")
                        break
                    
                    # Если нет товаров, но есть total и scroll_id - пробуем еще раз
                    if total > 0 and total_fetched < total and new_scroll_id:
                        print(f" [⚠️] Пустой ответ #{empty_responses_in_row}, но total={total}, загружено={total_fetched}. Пробуем еще раз...")
                        scroll_id = new_scroll_id
                        continue
                    
                    # Если нет товаров - завершаем (согласно документации API)
                    print(" [✅] Нет больше товаров")
                    break
                
                # Если загружено все товары согласно total
                if total > 0 and total_fetched >= total:
                    print(f" [✅] Загружено все ({total_fetched} из {total})")
                    break
                
                # Если нет scroll_id для следующего запроса - завершаем
                if not new_scroll_id:
                    # Но проверяем total, может быть мы не все загрузили
                    if total > 0 and total_fetched < total:
                        print(f" [⚠️] Нет scroll_id, но загружено {total_fetched} из {total}. Возможна потеря данных.")
                    print("[🏁] Достигнут конец списка товаров")
                    break
                
            except Exception as e:
                print(f"\n[❌] Непредвиденная ошибка: {e}")
                # Сохраняем то, что успели получить
                print(f"[⚠️] Прерываем загрузку. Сохраняем {len(all_products)} полученных товаров.")
                return all_products
    
    return all_products


def save_products_to_json(products, filename=None):
    """
    Сохранить товары в JSON файл
    
    Args:
        products (list): Список товаров для сохранения
        filename (str, optional): Имя файла. Если None, будет сгенерировано автоматически.
    
    Returns:
        str: Имя файла, в который были сохранены данные
        
    Raises:
        Exception: При ошибке сохранения файла
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"catalog21_products_{timestamp}.json"
    
    print(f"[💾] Сохраняем {len(products)} товаров из каталога ID {CATALOG_ID} в файл: {filename}")
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        print(f"[✅] Файл успешно сохранен: {filename}")
        return filename
    except Exception as e:
        print(f"[❌] Ошибка при сохранении в JSON: {e}")
        # Попробуем сохранить в другой файл с префиксом recovery
        try:
            recovery_filename = f"recovery_catalog21_{timestamp}.json"
            print(f"[🔄] Пытаемся сохранить в файл восстановления: {recovery_filename}")
            with open(recovery_filename, 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            print(f"[✅] Файл восстановления успешно сохранен: {recovery_filename}")
            return recovery_filename
        except Exception as e2:
            print(f"[❌] Критическая ошибка при сохранении файла восстановления: {e2}")
            raise


async def main_async():
    """
    Основная асинхронная функция скрипта
    
    Координирует процесс авторизации, загрузки товаров и сохранения их в файл.
    Обрабатывает исключения и выводит информацию о прогрессе.
    """
    print("[📦] Скрипт выгрузки всех товаров из каталога ID 21 из Compo PIM API")
    print(f"🔗 API URL: {PIM_API_URL}")
    print(f"📚 Каталог ID: {CATALOG_ID}\n")
    
    # Проверяем наличие необходимых переменных окружения
    if not all([PIM_LOGIN, PIM_PASSWORD]):
        print("[❌] Необходимо установить переменные окружения PIM_LOGIN и PIM_PASSWORD")
        return
    
    try:
        # Авторизация
        token = await authenticate()
        
        # Загрузка товаров из каталога ID 21
        products = await fetch_catalog21_products(token)
        
        if products:
            print(f"\n📊 Всего загружено товаров из каталога ID {CATALOG_ID}: {len(products)}")
            
            # Сохранение в JSON
            filename = save_products_to_json(products)
            
            print(f"\n🎉 Завершено! Товары из каталога ID {CATALOG_ID} сохранены в файл: {filename}")
        else:
            print(f"\n❌ Не удалось загрузить товары из каталога ID {CATALOG_ID}")
    
    except httpx.RequestError as e:
        # Ошибки подключения: таймауты, проблемы с DNS и т.д.
        print(f"❌ Ошибка подключения: {e}")
    except httpx.HTTPStatusError as e:
        # Ошибки HTTP статусов (4XX, 5XX)
        print(f"❌ Ошибка HTTP: {e}")
    except Exception as e:
        # Все остальные ошибки
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


def main():
    """
    Точка входа для запуска асинхронной функции
    
    Запускает асинхронный цикл asyncio и исполняет main_async()
    """
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[⚠️] Скрипт прерван пользователем")


if __name__ == "__main__":
    main()