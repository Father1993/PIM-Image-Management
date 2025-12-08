#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для поиска товаров из Supabase таблицы products без значения matrix.
Сохраняет результаты в Excel файл.
"""

import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OUTPUT_FILE = f"products_without_matrix_supabase_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"


def main():
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Подключение к Supabase установлено")
        
        print("📥 Поиск товаров без значения matrix...")
        
        response = (
            supabase.table("products")
            .select("id, product_name, article, code_1c")
            .is_("matrix", "null")
            .execute()
        )
        
        products = response.data or []
        
        products_without_matrix = []
        for product in products:
            products_without_matrix.append({
                "header": product.get("product_name", ""),
                "КОД_1С": product.get("code_1c") or product.get("article", ""),
                "id": product.get("id")
            })
        
        if not products_without_matrix:
            print("✅ Товаров без значения matrix не найдено")
            return
        
        df = pd.DataFrame(products_without_matrix)
        df.to_excel(OUTPUT_FILE, index=False, engine="openpyxl")
        
        print(f"\n✅ Найдено {len(products_without_matrix)} товаров без значения matrix")
        print(f"💾 Результаты сохранены в {OUTPUT_FILE}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

