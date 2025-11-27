#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для синхронизации новых товаров из onec_catalog в new_onec_products
Сравнивает code_1c с таблицей products и добавляет только отсутствующие товары
"""

import os
import asyncio
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def safe_get(item, key):
    """Безопасное получение значения с проверкой на None и пустую строку"""
    value = item.get(key)
    if value is None:
        return None
    # Числовые поля конвертируем в строку (включая 0)
    if isinstance(value, (int, float)):
        return str(value)
    # Текстовые поля
    value_str = str(value).strip()
    return value_str if value_str else None


def prepare_product(item):
    """Подготовка данных товара для вставки в new_onec_products"""
    return {
        "product_name": safe_get(item, "product_name"),
        "article": safe_get(item, "article"),
        "code_1c": safe_get(item, "code_1c"),
        "barcode": safe_get(item, "barcode"),
        "provider": safe_get(item, "provider"),
        "brand": safe_get(item, "brand"),
        "weight": safe_get(item, "weight"),
        "volume": safe_get(item, "volume"),
        "length": safe_get(item, "length"),
        "matrix": safe_get(item, "matrix"),
        "image_file": safe_get(item, "image_file"),
        "group1": safe_get(item, "group1"),
        "group2": safe_get(item, "group2"),
        "group3": safe_get(item, "group3"),
        "group4": safe_get(item, "group4"),
        "group5": safe_get(item, "group5"),
        "group6": safe_get(item, "group6"),
        "group7": safe_get(item, "group7"),
        "group8": safe_get(item, "group8"),
        "group9": safe_get(item, "group9"),
        "group10": safe_get(item, "group10"),
    }


async def main():
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Подключение к Supabase установлено")

        # Получаем все code_1c из products
        print("📊 Загрузка code_1c из таблицы products...")
        response = client.table("products").select("code_1c").execute()
        total_products = len(response.data)
        existing_codes = set()
        products_without_code = 0
        
        for item in response.data:
            code = item.get("code_1c")
            if code:
                code_str = str(code).strip()
                if code_str:
                    existing_codes.add(code_str)
                else:
                    products_without_code += 1
            else:
                products_without_code += 1
        
        print(f"✅ Всего записей в products: {total_products}")
        print(f"✅ Уникальных code_1c в products: {len(existing_codes)}")
        print(f"✅ Записей без code_1c: {products_without_code}")

        # Получаем все товары из onec_catalog
        print("📦 Загрузка товаров из onec_catalog...")
        all_products = []
        offset = 0
        limit = 1000

        while True:
            response = client.table("onec_catalog").select("*").range(offset, offset + limit - 1).execute()
            if not response.data:
                break
            all_products.extend(response.data)
            offset += limit
            print(f"   Загружено {len(all_products)} товаров...")

        print(f"✅ Всего товаров в onec_catalog: {len(all_products)}")

        # Анализ данных
        print("🔍 Анализ данных...")
        codes_in_onec = {}
        without_code = 0
        
        for item in all_products:
            code = str(item.get("code_1c", "")).strip()
            if not code:
                without_code += 1
                continue
            if code not in codes_in_onec:
                codes_in_onec[code] = []
            codes_in_onec[code].append(item)
        
        unique_codes = len(codes_in_onec)
        duplicates = sum(1 for items in codes_in_onec.values() if len(items) > 1)
        duplicate_count = sum(len(items) - 1 for items in codes_in_onec.values() if len(items) > 1)
        
        print(f"   Уникальных code_1c в onec_catalog: {unique_codes}")
        print(f"   Товаров без code_1c: {without_code}")
        print(f"   Дубликатов code_1c: {duplicates} (лишних записей: {duplicate_count})")

        # Фильтруем новые товары (которых нет в products)
        # Берем только первую запись для каждого уникального code_1c
        print("🔍 Поиск новых товаров...")
        new_products = []
        added_codes = set()
        codes_in_onec_set = set(codes_in_onec.keys())
        codes_in_products_not_in_onec = existing_codes - codes_in_onec_set
        
        for item in all_products:
            code = str(item.get("code_1c", "")).strip()
            if code and code not in existing_codes and code not in added_codes:
                prepared = prepare_product(item)
                new_products.append(prepared)
                added_codes.add(code)
        
        if codes_in_products_not_in_onec:
            print(f"   ⚠️  В products найдено {len(codes_in_products_not_in_onec)} code_1c, которых нет в onec_catalog")

        print(f"\n📊 Статистика:")
        print(f"   Товаров в onec_catalog: {len(all_products)}")
        print(f"   Уникальных code_1c в onec_catalog: {unique_codes}")
        print(f"   Всего записей в products: {total_products}")
        print(f"   Уникальных code_1c в products: {len(existing_codes)}")
        print(f"   Ожидаемо новых товаров: {unique_codes - len(existing_codes)}")
        print(f"   🆕 Новых товаров для добавления: {len(new_products)}")
        
        if len(new_products) != unique_codes - len(existing_codes):
            print(f"\n⚠️  Внимание: Расхождение!")
            print(f"   Ожидалось: {unique_codes - len(existing_codes)}")
            print(f"   Найдено: {len(new_products)}")
            print(f"   Разница: {len(new_products) - (unique_codes - len(existing_codes))}")

        if not new_products:
            print("✅ Новых товаров не найдено")
            return

        # Вставляем новые товары в new_onec_products
        print(f"\n💾 Добавление {len(new_products)} товаров в new_onec_products...")
        batch_size = 100
        total_inserted = 0

        for i in range(0, len(new_products), batch_size):
            batch = new_products[i:i + batch_size]
            
            try:
                response = client.table("new_onec_products").insert(batch).execute()
                inserted = len(response.data) if response.data else len(batch)
                total_inserted += inserted
                print(f"   ✅ Добавлено {total_inserted}/{len(new_products)} товаров")
            except Exception as e:
                print(f"❌ Ошибка при добавлении батча: {e}")
                raise

        print(f"\n🎉 Синхронизация завершена! Добавлено {total_inserted} новых товаров")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

