#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для обновления поля matrix у существующих товаров из JSON файла 1С
Обновляет только товары, у которых matrix отсутствует или пустое
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

        # Получаем товары без matrix или с пустым matrix
        print("📊 Загрузка товаров без matrix из базы...")
        response = client.table("products").select("id, code_1c, matrix").execute()
        
        # Фильтруем товары без matrix
        products_without_matrix = {}
        for product in response.data or []:
            code = str(product.get("code_1c", "")).strip()
            matrix = product.get("matrix")
            if code and (not matrix or not str(matrix).strip()):
                products_without_matrix[code] = product.get("id")
        
        print(f"✅ Найдено {len(products_without_matrix)} товаров без matrix")

        if not products_without_matrix:
            print("✅ Все товары уже имеют matrix")
            return

        # Загружаем JSON файл
        print(f"📂 Загрузка данных из {JSON_FILE}...")
        with open(JSON_FILE, "r", encoding="utf-8-sig") as f:
            products_json = json.load(f)
        print(f"✅ Загружено {len(products_json)} товаров из JSON")

        # Создаем словарь для быстрого поиска по коду
        json_matrix_map = {}
        for product_json in products_json:
            code = str(product_json.get("Code", "")).strip()
            matrix = product_json.get("Matrix", "").strip()
            if code and matrix:
                json_matrix_map[code] = matrix

        print(f"✅ Найдено {len(json_matrix_map)} товаров с matrix в JSON")

        # Подготавливаем обновления
        updates = []
        for code, product_id in products_without_matrix.items():
            if code in json_matrix_map:
                updates.append({
                    "id": product_id,
                    "matrix": json_matrix_map[code]
                })

        print(f"\n📊 Статистика:")
        print(f"   Товаров без matrix в базе: {len(products_without_matrix)}")
        print(f"   Товаров с matrix в JSON: {len(json_matrix_map)}")
        print(f"   🆕 Товаров для обновления: {len(updates)}")

        if not updates:
            print("✅ Нет товаров для обновления")
            return

        # Группируем обновления по значению matrix для более эффективного обновления
        matrix_groups = {}
        for update in updates:
            matrix = update["matrix"]
            if matrix not in matrix_groups:
                matrix_groups[matrix] = []
            matrix_groups[matrix].append(update["id"])

        print(f"📦 Группировка: {len(matrix_groups)} уникальных значений matrix")

        # Обновляем группами по значению matrix, разбивая большие группы на батчи
        total_updated = 0
        batch_size = 500  # Максимальное количество ID в одном запросе
        group_num = 0

        for matrix, product_ids in matrix_groups.items():
            group_num += 1
            # Разбиваем большие группы на батчи
            for i in range(0, len(product_ids), batch_size):
                batch_ids = product_ids[i : i + batch_size]
                try:
                    client.table("products").update({
                        "matrix": matrix
                    }).in_("id", batch_ids).execute()
                    
                    total_updated += len(batch_ids)
                except Exception as e:
                    print(f"❌ Ошибка при обновлении группы {group_num} (matrix={matrix}, батч {i//batch_size + 1}): {e}")
                    raise
            
            if group_num % 5 == 0 or total_updated == len(updates):
                print(f"📝 Обновлено {total_updated}/{len(updates)} товаров ({group_num}/{len(matrix_groups)} групп)")

        print(f"🎉 Обновление завершено! Обновлено {total_updated} товаров")

    except FileNotFoundError:
        print(f"❌ Файл {JSON_FILE} не найден")
    except Exception as e:
        print(f"❌ Ошибка при выполнении скрипта: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

