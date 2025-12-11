#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экспорт категорий с подтверждёнными описаниями для загрузки в 1С.
Структура: id, description, level, parent_id, header
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = "categories"
OUTPUT_FILE = "data/confirmed_categories_export.json"


def export_confirmed_categories():
    """Экспорт категорий с description_confirmed = true"""
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("📥 Загрузка категорий с подтверждёнными описаниями...")
    
    # Выбираем только нужные поля с фильтром
    response = (
        client.table(TABLE_NAME)
        .select("id,description,level,parent_id,header")
        .eq("description_confirmed", True)
        .execute()
    )
    
    categories = response.data or []
    
    if not categories:
        print("❌ Категории не найдены")
        return
    
    print(f"✅ Найдено {len(categories)} категорий")
    
    # Формируем результат с нужной структурой
    result = []
    category_ids = []
    
    for category in categories:
        category_ids.append(category.get("id"))
        result.append({
            "id": category.get("id"),
            "description": category.get("description") or "",
            "level": category.get("level"),
            "parent_id": category.get("parent_id"),
            "header": category.get("header") or ""
        })
    
    # Сохраняем в JSON
    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Данные сохранены в {output_path}")
    print(f"📊 Всего записей: {len(result)}")
    
    # Устанавливаем флаг description_sent_to_1c = true
    if category_ids:
        print(f"\n🔄 Установка флага description_sent_to_1c = true...")
        
        # Обновляем батчами
        BATCH_SIZE = 500
        updated_count = 0
        
        for i in range(0, len(category_ids), BATCH_SIZE):
            batch_ids = category_ids[i:i + BATCH_SIZE]
            
            client.table(TABLE_NAME)\
                .update({"description_sent_to_1c": True})\
                .in_("id", batch_ids)\
                .execute()
            
            updated_count += len(batch_ids)
            print(f"✅ Обновлено: {updated_count}/{len(category_ids)}")
        
        print(f"✅ Флаг description_sent_to_1c установлен для {updated_count} категорий")


if __name__ == "__main__":
    try:
        export_confirmed_categories()
    except Exception as exc:
        print(f"❌ Ошибка: {exc}")
        import traceback
        traceback.print_exc()

