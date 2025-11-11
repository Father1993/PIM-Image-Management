#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Асинхронный скрипт для обновления полей товаров из JSON файла в таблицу products в Supabase
Обновляет: brend, volume, mass, length, product_group по code_1c
"""

import os
import json
import asyncio
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
JSON_FILE = "catalog_json/new-catalog-10-11.json"


def normalize_value(value):
    """Нормализует значение: убирает пробелы, возвращает None для пустых строк"""
    if value is None:
        return None
    value_str = str(value).strip()
    return value_str if value_str else None


def update_product_sync(client, product_id, update_data, max_retries=3):
    """Синхронное обновление одного товара с retry"""
    import time
    
    for attempt in range(max_retries):
        try:
            client.table("products").update(update_data).eq("id", product_id).execute()
            return True
        except Exception as e:
            error_str = str(e)
            # Проверяем, является ли это ошибкой сокета
            if "10035" in error_str or "socket" in error_str.lower() or "WinError" in error_str:
                if attempt < max_retries - 1:
                    # Небольшая задержка перед повтором
                    time.sleep(0.1 * (attempt + 1))
                    continue
            # Для других ошибок или последней попытки - логируем
            if attempt == max_retries - 1:
                print(f"❌ Ошибка обновления товара {product_id} после {max_retries} попыток: {e}")
            return False
    return False


async def update_product_async(client, product_id, update_data):
    """Асинхронное обновление одного товара"""
    return await asyncio.to_thread(update_product_sync, client, product_id, update_data)


async def update_batch_async(client, batch, semaphore, batch_num, total_batches):
    """Асинхронное обновление батча товаров"""
    async def update_with_semaphore(update_item):
        async with semaphore:
            return await update_product_async(
                client,
                update_item["id"],
                {
                    "brend": update_item["brend"],
                    "volume": update_item["volume"],
                    "mass": update_item["mass"],
                    "length": update_item["length"],
                    "product_group": update_item["product_group"],
                }
            )
    
    tasks = [update_with_semaphore(item) for item in batch]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    success_count = sum(1 for r in results if r is True)
    print(f"📝 Батч {batch_num}/{total_batches}: обновлено {success_count}/{len(batch)} товаров")
    return success_count


async def main():
    try:
        # Подключение к Supabase
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Подключение к базе данных установлено")

        # Загружаем JSON файл
        print(f"📂 Загрузка данных из {JSON_FILE}...")
        with open(JSON_FILE, "r", encoding="utf-8-sig") as f:
            products_json = json.load(f)
        print(f"✅ Загружено {len(products_json)} товаров из JSON")

        # Создаем словарь для быстрого поиска по code_1c
        print("🔄 Создание индекса данных из JSON...")
        json_data = {}
        for product in products_json:
            code = normalize_value(product.get("Code"))
            if code:
                json_data[code] = {
                    "brend": normalize_value(product.get("Brend")),
                    "volume": normalize_value(product.get("Volume")),
                    "mass": normalize_value(product.get("Mass")),
                    "length": normalize_value(product.get("length")),
                    "product_group": normalize_value(product.get("Group")),
                }
        print(f"✅ Индексировано {len(json_data)} товаров")

        # Получаем все товары из базы
        print("📊 Загрузка товаров из базы...")
        response = client.table("products").select("id, code_1c").execute()
        db_products = response.data or []
        print(f"✅ Найдено {len(db_products)} товаров в базе")

        # Подготавливаем данные для обновления
        print("\n🔄 Подготовка данных для обновления...")
        updates = []
        not_found_count = 0

        for product in db_products:
            code_1c = normalize_value(product.get("code_1c"))
            if not code_1c:
                continue

            json_product = json_data.get(code_1c)
            if not json_product:
                not_found_count += 1
                continue

            updates.append({
                "id": product.get("id"),
                "brend": json_product["brend"],
                "volume": json_product["volume"],
                "mass": json_product["mass"],
                "length": json_product["length"],
                "product_group": json_product["product_group"],
            })

        print(f"✅ Подготовлено {len(updates)} товаров для обновления")

        # Обновляем товары батчами асинхронно (последовательно по батчам, параллельно внутри батча)
        batch_size = 100
        total_batches = (len(updates) + batch_size - 1) // batch_size
        semaphore = asyncio.Semaphore(10)  # До 10 параллельных обновлений (меньше для Windows)

        print(f"\n💾 Обновление {len(updates)} товаров в {total_batches} батчах...")

        batches = [
            updates[i : i + batch_size]
            for i in range(0, len(updates), batch_size)
        ]

        # Обрабатываем батчи последовательно, но внутри батча параллельно
        updated_count = 0
        for idx, batch in enumerate(batches, 1):
            result = await update_batch_async(client, batch, semaphore, idx, total_batches)
            updated_count += result
            # Небольшая пауза между батчами для стабильности
            if idx < total_batches:
                await asyncio.sleep(0.1)

        print(f"\n📊 Статистика обновления:")
        print(f"   Всего товаров в базе: {len(db_products)}")
        print(f"   Товаров обновлено: {updated_count}")
        print(f"   Товаров не найдено в JSON: {not_found_count}")
        print(f"\n🎉 Обновление завершено!")

    except FileNotFoundError:
        print(f"❌ Файл {JSON_FILE} не найден")
    except Exception as e:
        print(f"❌ Ошибка при выполнении скрипта: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

