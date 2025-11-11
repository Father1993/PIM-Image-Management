#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для сравнения товаров из JSON с товарами в базе данных
"""

import os
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
JSON_FILE = "Catalog-Pim_01.11.25.json"


def main():
    try:
        # Подключение к Supabase
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Подключение к базе данных установлено")

        # Получаем все товары из базы
        print("📊 Загрузка товаров из базы...")
        response = client.table("products").select("code_1c").execute()
        db_codes = {str(item.get("code_1c", "")).strip() for item in (response.data or []) if item.get("code_1c")}
        print(f"✅ Найдено {len(db_codes)} товаров в базе")

        # Загружаем JSON
        print(f"📂 Загрузка данных из {JSON_FILE}...")
        with open(JSON_FILE, "r", encoding="utf-8-sig") as f:
            products_json = json.load(f)
        
        json_codes = {str(p.get("Code", "")).strip() for p in products_json if p.get("Code")}
        print(f"✅ Загружено {len(products_json)} товаров из JSON")
        print(f"✅ Уникальных кодов в JSON: {len(json_codes)}")

        # Анализ
        in_both = json_codes & db_codes
        only_in_json = json_codes - db_codes
        only_in_db = db_codes - json_codes

        print(f"\n📊 Сравнение:")
        print(f"   Товаров в обоих источниках: {len(in_both)}")
        print(f"   Товаров только в JSON (нет в базе): {len(only_in_json)}")
        print(f"   Товаров только в базе (нет в JSON): {len(only_in_db)}")

        if only_in_json:
            print(f"\n⚠️ Примеры товаров только в JSON (первые 5):")
            for i, code in enumerate(list(only_in_json)[:5], 1):
                print(f"   {i}. Code: {code}")

        if only_in_db:
            print(f"\nℹ️ Примеры товаров только в базе (первые 5):")
            for i, code in enumerate(list(only_in_db)[:5], 1):
                print(f"   {i}. Code: {code}")

        print(f"\n✅ Анализ завершен")

    except FileNotFoundError:
        print(f"❌ Файл {JSON_FILE} не найден")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

