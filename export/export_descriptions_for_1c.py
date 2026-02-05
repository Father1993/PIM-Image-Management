#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экспорт товаров с неотправленными описаниями в 1С.
Выбирает товары где description_sent_to_1c = false.
Экспортирует только нужные поля: code_1c, GUID, product_name, description, short_description.
"""

import os
import json
from datetime import datetime, UTC
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = "products"
OUTPUT_FILE = "data/descriptions_for_1c_export.json"


def export_products_for_1c():
    """Экспорт товаров с description_sent_to_1c = false"""
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("📥 Загрузка товаров с неотправленными описаниями в 1С...")
    
    # Выбираем только нужные поля для 1С
    response = (
        client.table(TABLE_NAME)
        .select("code_1c,GUID,product_name,description,short_description")
        .eq("description_sent_to_1c", False)
        .execute()
    )
    
    products = response.data or []
    
    if not products:
        print("❌ Товары не найдены (все описания уже отправлены в 1С)")
        return
    
    # Подсчитываем статистику
    total = len(products)
    with_description = sum(1 for p in products if p.get("description"))
    with_short_description = sum(1 for p in products if p.get("short_description"))
    with_code_1c = sum(1 for p in products if p.get("code_1c"))
    with_guid = sum(1 for p in products if p.get("GUID"))
    
    # Формируем чистый результат
    result = []
    for product in products:
        result.append({
            "code_1c": product.get("code_1c") or "",
            "GUID": str(product.get("GUID")) if product.get("GUID") else "",
            "product_name": product.get("product_name") or "",
            "description": product.get("description") or "",
            "short_description": product.get("short_description") or ""
        })
    
    # Сохраняем в JSON
    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # Выводим статистику
    print(f"\n✅ Экспорт завершён")
    print(f"\n📊 Статистика:")
    print(f"   • Всего товаров в файле: {total}")
    print(f"   • С описанием: {with_description}")
    print(f"   • С кратким описанием: {with_short_description}")
    print(f"   • С кодом 1С: {with_code_1c}")
    print(f"   • С GUID: {with_guid}")
    
    print(f"\n💾 Файл сохранён: {output_path}")
    print(f"📦 Размер файла: {output_path.stat().st_size / 1024:.2f} KB")


if __name__ == "__main__":
    try:
        export_products_for_1c()
    except Exception as exc:
        print(f"❌ Ошибка: {exc}")
        import traceback
        traceback.print_exc()
