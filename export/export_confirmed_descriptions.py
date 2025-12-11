#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экспорт товаров с подтверждёнными описаниями для загрузки в 1С.
Структура: code_1c, GUID, product_name, description, short_description
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = "products"
OUTPUT_FILE = "data/confirmed_descriptions_export.json"


def export_confirmed_descriptions():
    """Экспорт товаров с description_confirmed = true"""
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("📥 Загрузка товаров с подтверждёнными описаниями...")
    
    # Выбираем только нужные поля с фильтром
    response = (
        client.table(TABLE_NAME)
        .select("code_1c,GUID,product_name,description,short_description")
        .eq("description_confirmed", True)
        .execute()
    )
    
    products = response.data or []
    
    if not products:
        print("❌ Товары не найдены")
        return
    
    print(f"✅ Найдено {len(products)} товаров")
    
    # Формируем результат с нужной структурой
    result = []
    for product in products:
        result.append({
            "code_1c": product.get("code_1c") or "",
            "GUID": str(product.get("GUID") or ""),
            "product_name": product.get("product_name") or "",
            "description": product.get("description") or "",
            "short_description": product.get("short_description") or ""
        })
    
    # Сохраняем в JSON
    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Данные сохранены в {output_path}")
    print(f"📊 Всего записей: {len(result)}")


if __name__ == "__main__":
    try:
        export_confirmed_descriptions()
    except Exception as exc:
        print(f"❌ Ошибка: {exc}")
        import traceback
        traceback.print_exc()

