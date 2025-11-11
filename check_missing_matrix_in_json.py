#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки, есть ли товары без matrix в JSON файле
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

        # Получаем товары без matrix из базы
        print("📊 Загрузка товаров без matrix из базы...")
        response = client.table("products").select("id, code_1c, matrix").execute()
        
        products_without_matrix = []
        for product in response.data or []:
            code = str(product.get("code_1c", "")).strip()
            matrix = product.get("matrix")
            if code and (not matrix or not str(matrix).strip()):
                products_without_matrix.append({
                    "id": product.get("id"),
                    "code_1c": code
                })
        
        print(f"✅ Найдено {len(products_without_matrix)} товаров без matrix в базе")

        if not products_without_matrix:
            print("✅ Все товары имеют matrix")
            return

        # Загружаем JSON файл
        print(f"📂 Загрузка данных из {JSON_FILE}...")
        with open(JSON_FILE, "r", encoding="utf-8-sig") as f:
            products_json = json.load(f)
        print(f"✅ Загружено {len(products_json)} товаров из JSON")

        # Создаем словарь кодов из JSON
        json_codes = {}
        for product_json in products_json:
            code = str(product_json.get("Code", "")).strip()
            matrix = product_json.get("Matrix", "").strip()
            if code:
                json_codes[code] = {
                    "has_matrix": bool(matrix),
                    "matrix": matrix
                }

        print(f"✅ Найдено {len(json_codes)} уникальных кодов в JSON")

        # Проверяем товары без matrix
        in_json = 0
        not_in_json = 0
        in_json_without_matrix = 0
        in_json_with_matrix = 0

        print(f"\n📊 Анализ товаров без matrix:")
        for product in products_without_matrix:
            code = product["code_1c"]
            if code in json_codes:
                in_json += 1
                if json_codes[code]["has_matrix"]:
                    in_json_with_matrix += 1
                else:
                    in_json_without_matrix += 1
            else:
                not_in_json += 1

        print(f"   Товаров в JSON: {in_json}")
        print(f"      - С matrix в JSON: {in_json_with_matrix} (можно обновить)")
        print(f"      - Без matrix в JSON: {in_json_without_matrix} (нет данных)")
        print(f"   Товаров нет в JSON: {not_in_json} (нет в экспорте)")

        if in_json_with_matrix > 0:
            print(f"\n⚠️ Найдено {in_json_with_matrix} товаров, которые можно обновить!")
            print(f"   Эти товары есть в JSON с matrix, но почему-то не были обновлены")
            print(f"   Возможно, нужно запустить update_matrix_from_1c.py еще раз")

        if not_in_json > 0:
            print(f"\nℹ️ {not_in_json} товаров отсутствуют в JSON файле")
            print(f"   Эти товары есть только в базе и не были в экспорте из 1С")

        print(f"\n✅ Проверка завершена")

    except FileNotFoundError:
        print(f"❌ Файл {JSON_FILE} не найден")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

