#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для экспорта товаров из products, которых нет в onec_catalog (выведены из 1С)
Экспортирует в Excel файл с полями: название, артикул, код1с, link_pim, GUID, barcode, provider, matrix, brend, product_group
"""

import os
import pandas as pd
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def main():
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Подключение к Supabase установлено")

        # Получаем все code_1c из onec_catalog
        print("📊 Загрузка code_1c из таблицы onec_catalog...")
        onec_codes = set()
        offset = 0
        limit = 1000

        while True:
            response = client.table("onec_catalog").select("code_1c").range(offset, offset + limit - 1).execute()
            if not response.data:
                break
            for item in response.data:
                code = item.get("code_1c")
                if code:
                    code_str = str(code).strip()
                    if code_str:
                        onec_codes.add(code_str)
            offset += limit
            print(f"   Загружено {len(onec_codes)} уникальных кодов...")

        print(f"✅ Уникальных code_1c в onec_catalog: {len(onec_codes)}")

        # Получаем все code_1c из products (без пагинации, как в sync скрипте)
        print("📊 Загрузка code_1c из таблицы products...")
        response = client.table("products").select("code_1c").execute()
        total_products = len(response.data)
        products_codes_set = set()
        products_without_code = 0
        
        for item in response.data:
            code = item.get("code_1c")
            if code:
                code_str = str(code).strip()
                if code_str:
                    products_codes_set.add(code_str)
                else:
                    products_without_code += 1
            else:
                products_without_code += 1
        
        print(f"✅ Всего записей в products: {total_products}")
        print(f"✅ Уникальных code_1c в products: {len(products_codes_set)}")
        print(f"✅ Записей без code_1c: {products_without_code}")

        # Находим коды из products, которых нет в onec_catalog
        codes_in_products_not_in_onec = products_codes_set - onec_codes
        
        print(f"\n📊 Статистика:")
        print(f"   Уникальных code_1c в onec_catalog: {len(onec_codes)}")
        print(f"   Уникальных code_1c в products: {len(products_codes_set)}")
        print(f"   Товаров без code_1c в products: {products_without_code}")
        print(f"   Уникальных code_1c в products, которых нет в onec_catalog: {len(codes_in_products_not_in_onec)}")

        if not codes_in_products_not_in_onec:
            print("✅ Товаров, выведенных из 1С, не найдено")
            return

        # Загружаем товары пакетами по code_1c (используя IN запросы для гарантированной загрузки всех)
        print("📦 Загрузка товаров из products для экспорта...")
        removed_products = []
        codes_list = list(codes_in_products_not_in_onec)
        batch_size = 100  # Supabase ограничение на IN запросы

        for i in range(0, len(codes_list), batch_size):
            batch_codes = codes_list[i:i + batch_size]
            response = client.table("products").select(
                "id, product_name, article, code_1c, link_pim, uid, barcode, provider, matrix, brend, product_group"
            ).in_("code_1c", batch_codes).execute()
            
            if response.data:
                for product in response.data:
                    code = str(product.get("code_1c", "")).strip()
                    if code and code in codes_in_products_not_in_onec:
                        # Проверяем, не добавлен ли уже этот код (на случай дубликатов)
                        if not any(p["Код1С"] == code for p in removed_products):
                            removed_products.append({
                                "Название": product.get("product_name") or "",
                                "Артикул": product.get("article") or "",
                                "Код1С": code,
                                "link_pim": product.get("link_pim") or "",
                                "GUID": str(product.get("uid")) if product.get("uid") else "",
                                "barcode": product.get("barcode") or "",
                                "provider": product.get("provider") or "",
                                "matrix": product.get("matrix") or "",
                                "brend": product.get("brend") or "",
                                "product_group": product.get("product_group") or "",
                            })
            
            print(f"   Обработано {min(i + batch_size, len(codes_list))}/{len(codes_list)} кодов, найдено {len(removed_products)} товаров...")

        print(f"\n✅ Найдено {len(removed_products)} уникальных товаров, выведенных из 1С")

        if not removed_products:
            print("✅ Товаров, выведенных из 1С, не найдено")
            return

        # Создаем DataFrame и экспортируем в Excel
        df = pd.DataFrame(removed_products)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"removed_from_1c_products_{timestamp}.xlsx"

        df.to_excel(filename, index=False, engine="openpyxl")
        print(f"\n🎉 Экспорт завершен!")
        print(f"   Файл: {filename}")
        print(f"   Товаров экспортировано: {len(removed_products)}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

