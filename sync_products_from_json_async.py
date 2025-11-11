#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Асинхронный скрипт для синхронизации товаров из JSON в таблицу products в Supabase
Проверяет по code_1c и создает только новые товары
"""

import os
import json
import uuid
import asyncio
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
JSON_FILE = "catalog_json/new-catalog-10-11.json"


def format_list_to_string(items):
    """Преобразует список в строку через запятую, пропуская пустые значения"""
    if not items:
        return None
    filtered = [str(item).strip() for item in items if str(item).strip()]
    return ", ".join(filtered) if filtered else None


def normalize_value(value):
    """Нормализует значение: убирает пробелы, возвращает None для пустых строк"""
    if value is None:
        return None
    value_str = str(value).strip()
    return value_str if value_str else None


def prepare_product(product_json):
    """Подготавливает данные товара для вставки в базу"""
    code = str(product_json.get("Code", "")).strip()
    if not code:
        return None

    return {
        "uid": str(uuid.uuid4()),
        "code_1c": code,
        "product_name": product_json.get("Name", "").strip() or None,
        "barcode": format_list_to_string(product_json.get("Barcode", [])),
        "provider": format_list_to_string(product_json.get("Vendor", [])),
        "matrix": product_json.get("Matrix", "").strip() or None,
        "brend": normalize_value(product_json.get("Brend")),
        "volume": normalize_value(product_json.get("Volume")),
        "mass": normalize_value(product_json.get("Mass")),
        "length": normalize_value(product_json.get("length")),
        "product_group": normalize_value(product_json.get("Group")),
        "is_new": True,
    }


async def main():
    try:
        # Подключение к Supabase
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Подключение к базе данных установлено")

        # Получаем все существующие code_1c и отрицательные ID из таблицы products
        print("📊 Загрузка существующих товаров из базы...")
        response = client.table("products").select("code_1c, id").execute()
        existing_codes = {
            str(item.get("code_1c", "")).strip()
            for item in (response.data or [])
            if item.get("code_1c")
        }
        
        # Находим минимальный отрицательный ID (самый отрицательный)
        negative_ids = [
            item.get("id") for item in (response.data or []) if item.get("id") and item.get("id") < 0
        ]
        min_negative_id = min(negative_ids) if negative_ids else 0
        
        print(f"✅ Найдено {len(existing_codes)} товаров в базе")
        if min_negative_id < 0:
            print(f"✅ Минимальный отрицательный ID в базе: {min_negative_id}")

        # Загружаем JSON файл
        print(f"📂 Загрузка данных из {JSON_FILE}...")
        with open(JSON_FILE, "r", encoding="utf-8-sig") as f:
            products_json = json.load(f)
        print(f"✅ Загружено {len(products_json)} товаров из JSON")

        # Фильтруем новые товары
        print("🔄 Фильтрация новых товаров...")
        new_products = []
        without_code = 0
        already_exists = 0

        for product_json in products_json:
            code = str(product_json.get("Code", "")).strip()
            if not code:
                without_code += 1
                continue
            if code in existing_codes:
                already_exists += 1
                continue
            prepared = prepare_product(product_json)
            if prepared:
                new_products.append(prepared)

        print(f"\n📊 Статистика обработки:")
        print(f"   Всего товаров в JSON: {len(products_json)}")
        print(f"   Товаров без кода (Code): {without_code}")
        print(f"   Товаров уже есть в базе: {already_exists}")
        print(f"   🆕 Новых товаров для добавления: {len(new_products)}")

        if not new_products:
            print("✅ Все товары уже есть в базе")
            return

        # Добавляем временные отрицательные id для новых товаров (маркер новых товаров)
        # Начинаем с минимального отрицательного ID минус количество новых товаров
        start_id = min_negative_id - len(new_products) if min_negative_id < 0 else -len(new_products)
        
        for idx, product in enumerate(new_products):
            product["id"] = start_id - idx  # Отрицательный ID с минусом, начиная с безопасного значения

        # Вставляем новые товары пакетами последовательно (чтобы избежать конфликтов ID)
        batch_size = 100
        total_inserted = 0

        print(f"\n💾 Вставка {len(new_products)} товаров...")

        for i in range(0, len(new_products), batch_size):
            batch = new_products[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(new_products) + batch_size - 1) // batch_size
            
            try:
                response = client.table("products").insert(batch).execute()
                inserted_count = len(response.data) if response.data else len(batch)
                total_inserted += inserted_count
                print(f"📝 Вставлено {total_inserted}/{len(new_products)} товаров")
            except Exception as e:
                print(f"❌ Ошибка при вставке батча {batch_num}: {e}")
                print(f"Пример записи: {json.dumps(batch[0] if batch else {}, ensure_ascii=False, indent=2)}")
                raise

        print(f"\n🎉 Синхронизация завершена! Добавлено {total_inserted} новых товаров")

    except FileNotFoundError:
        print(f"❌ Файл {JSON_FILE} не найден")
    except Exception as e:
        print(f"❌ Ошибка при выполнении скрипта: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

