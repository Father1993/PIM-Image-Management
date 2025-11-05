#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для синхронизации товаров из 1С (JSON) в таблицу products в Supabase
Добавляет только новые товары, которых нет в базе
"""

import os
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
JSON_FILE = "Catalog-Pim_01.11.25.json"


def format_list_to_string(items):
    """Преобразует список в строку через запятую, пропуская пустые значения"""
    if not items:
        return None
    filtered = [str(item).strip() for item in items if str(item).strip()]
    return ", ".join(filtered) if filtered else None


def prepare_product(product_json):
    """Подготавливает данные товара для вставки в базу"""
    code = product_json.get("Code", "").strip()
    if not code:
        return None

    return {
        "code_1c": code,
        "product_name": product_json.get("Name", "").strip() or None,
        "barcode": format_list_to_string(product_json.get("Barcode", [])),
        "provider": format_list_to_string(product_json.get("Vendor", [])),
        "matrix": product_json.get("Matrix", "").strip() or None,
    }


def main():
    try:
        # Подключение к Supabase
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Подключение к базе данных установлено")

        # Получаем все существующие code_1c и максимальный id из таблицы products
        print("📊 Загрузка существующих товаров из базы...")
        response = client.table("products").select("code_1c, id").execute()
        existing_codes = {item.get("code_1c") for item in (response.data or []) if item.get("code_1c")}
        max_id = max([item.get("id", 0) for item in (response.data or []) if item.get("id")], default=0)
        print(f"✅ Найдено {len(existing_codes)} товаров в базе, максимальный id: {max_id}")

        # Загружаем JSON файл
        print(f"📂 Загрузка данных из {JSON_FILE}...")
        with open(JSON_FILE, "r", encoding="utf-8-sig") as f:
            products_json = json.load(f)
        print(f"✅ Загружено {len(products_json)} товаров из JSON")

        # Фильтруем новые товары
        new_products = []
        for product_json in products_json:
            code = product_json.get("Code", "").strip()
            if code and code not in existing_codes:
                prepared = prepare_product(product_json)
                if prepared:
                    new_products.append(prepared)

        print(f"🆕 Найдено {len(new_products)} новых товаров для добавления")

        if not new_products:
            print("✅ Все товары уже есть в базе")
            return

        # Добавляем id для новых товаров
        for idx, product in enumerate(new_products, start=1):
            product["id"] = max_id + idx

        # Вставляем новые товары пакетами
        batch_size = 100
        total_inserted = 0

        for i in range(0, len(new_products), batch_size):
            batch = new_products[i : i + batch_size]
            try:
                response = client.table("products").insert(batch).execute()
                inserted_count = len(response.data) if response.data else len(batch)
                total_inserted += inserted_count
                print(f"📝 Вставлено {total_inserted}/{len(new_products)} товаров")
            except Exception as e:
                print(f"❌ Ошибка при вставке батча {i//batch_size + 1}: {e}")
                print(f"Пример записи: {json.dumps(batch[0] if batch else {}, ensure_ascii=False, indent=2)}")
                raise

        print(f"🎉 Синхронизация завершена! Добавлено {total_inserted} новых товаров")

    except FileNotFoundError:
        print(f"❌ Файл {JSON_FILE} не найден")
    except Exception as e:
        print(f"❌ Ошибка при выполнении скрипта: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

