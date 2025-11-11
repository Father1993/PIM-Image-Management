#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для повторной обработки товаров с ошибками обновления
Использует больше попыток и меньший параллелизм для надежности
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


def update_product_sync(client, product_id, update_data, max_retries=10):
    """Синхронное обновление одного товара с большим количеством retry"""
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
                    # Увеличиваем задержку перед повтором
                    time.sleep(0.5 * (attempt + 1))
                    continue
            # Для других ошибок или последней попытки - логируем
            if attempt == max_retries - 1:
                print(f"❌ Ошибка обновления товара {product_id} после {max_retries} попыток: {e}")
            return False
    return False


async def update_product_async(client, product_id, update_data):
    """Асинхронное обновление одного товара"""
    return await asyncio.to_thread(update_product_sync, client, product_id, update_data)


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
        response = client.table("products").select("id, code_1c, brend, volume, mass, length, product_group").execute()
        db_products = response.data or []
        print(f"✅ Найдено {len(db_products)} товаров в базе")

        # Находим товары, которые нужно обновить (сравниваем с JSON)
        print("\n🔄 Поиск товаров для обновления...")
        updates = []
        
        for product in db_products:
            code_1c = normalize_value(product.get("code_1c"))
            if not code_1c:
                continue

            json_product = json_data.get(code_1c)
            if not json_product:
                continue

            # Проверяем, нужно ли обновлять (сравниваем значения)
            current_values = {
                "brend": normalize_value(product.get("brend")),
                "volume": normalize_value(product.get("volume")),
                "mass": normalize_value(product.get("mass")),
                "length": normalize_value(product.get("length")),
                "product_group": normalize_value(product.get("product_group")),
            }

            # Если значения отличаются, добавляем в список обновления
            if current_values != json_product:
                updates.append({
                    "id": product.get("id"),
                    "code_1c": code_1c,
                    "brend": json_product["brend"],
                    "volume": json_product["volume"],
                    "mass": json_product["mass"],
                    "length": json_product["length"],
                    "product_group": json_product["product_group"],
                })

        print(f"✅ Найдено {len(updates)} товаров для обновления")

        if not updates:
            print("✅ Все товары уже обновлены!")
            return

        # Обновляем товары с меньшим параллелизмом и большим количеством попыток
        semaphore = asyncio.Semaphore(5)  # Только 5 параллельных обновлений для надежности
        
        print(f"\n💾 Повторное обновление {len(updates)} товаров...")
        print("   (Используется 5 параллельных запросов и до 10 попыток на товар)")

        async def update_with_semaphore(update_item):
            async with semaphore:
                result = await update_product_async(
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
                if result:
                    print(f"✅ Обновлен товар {update_item['code_1c']} (ID: {update_item['id']})")
                return result

        # Обрабатываем небольшими батчами
        batch_size = 50
        updated_count = 0
        failed_items = []

        for i in range(0, len(updates), batch_size):
            batch = updates[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(updates) + batch_size - 1) // batch_size
            
            print(f"\n📦 Батч {batch_num}/{total_batches} ({len(batch)} товаров)...")
            
            tasks = [update_with_semaphore(item) for item in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for item, result in zip(batch, results):
                if result is True:
                    updated_count += 1
                else:
                    failed_items.append(item)
            
            print(f"   Обновлено: {updated_count} из {i + len(batch)}")
            
            # Пауза между батчами
            if i + batch_size < len(updates):
                await asyncio.sleep(0.5)

        print(f"\n📊 Статистика обновления:")
        print(f"   Всего товаров для обновления: {len(updates)}")
        print(f"   Товаров успешно обновлено: {updated_count}")
        print(f"   Товаров с ошибками: {len(failed_items)}")
        
        if failed_items:
            print(f"\n⚠️ Товары с ошибками (первые 10):")
            for item in failed_items[:10]:
                print(f"   - Code: {item['code_1c']}, ID: {item['id']}")
            if len(failed_items) > 10:
                print(f"   ... и еще {len(failed_items) - 10} товаров")

        print(f"\n🎉 Повторное обновление завершено!")

    except FileNotFoundError:
        print(f"❌ Файл {JSON_FILE} не найден")
    except Exception as e:
        print(f"❌ Ошибка при выполнении скрипта: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

