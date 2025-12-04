#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для экспорта товаров из таблицы new_onec_products в JSON
Структура: id -> {product_name, code_1c, article}
"""

import os
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OUTPUT_FILE = "products_export.json"


def main():
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Подключение к Supabase установлено")
        
        print("📊 Загрузка товаров из new_onec_products...")
        response = supabase.table("new_onec_products").select("id, product_name, code_1c, article").execute()
        products = response.data or []
        
        if not products:
            print("❌ Товары не найдены")
            return
        
        print(f"✅ Найдено {len(products)} товаров")
        
        # Формируем структуру: id -> {product_name, code_1c, article}
        result = {}
        for product in products:
            product_id = product.get("id")
            if product_id:
                result[product_id] = {
                    "product_name": product.get("product_name") or "",
                    "code_1c": product.get("code_1c") or "",
                    "article": product.get("article") or ""
                }
        
        # Сохраняем в JSON
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Данные сохранены в {OUTPUT_FILE}")
        print(f"📊 Всего записей: {len(result)}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

