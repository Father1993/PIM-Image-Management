#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Связывание товаров с каталогами.
Прямая связь: products.id = PIM product.id
"""

import json
import os
import sys

from dotenv import load_dotenv
from supabase import create_client, Client

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
CATALOG_JSON = "data/catalog_structure.json"
LINKS_JSON = "data/product_catalog_links.json"
BATCH_SIZE = 1000


def load_json(filepath: str) -> dict:
    """Загрузка JSON."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    """Основная функция."""
    print("🔗 СВЯЗЫВАНИЕ ТОВАРОВ С КАТАЛОГАМИ\n")
    
    # 1. Подключение к Supabase
    print("🔌 Подключение к Supabase...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Подключено\n")
    
    # 2. Загрузка каталогов в БД
    print("📂 Загрузка каталогов...")
    catalog_data = load_json(CATALOG_JSON)
    catalogs = catalog_data["catalogs"]
    
    # Создаем множество существующих ID для проверки
    existing_ids = {c["id"] for c in catalogs}
    
    # Сортируем по уровню - сначала родители, потом дети
    catalogs_sorted = sorted(catalogs, key=lambda x: x["level"])
    
    for i in range(0, len(catalogs_sorted), BATCH_SIZE):
        batch = catalogs_sorted[i:i + BATCH_SIZE]
        db_catalogs = [{
            "id": c["id"],
            "header": c["header"],
            "sync_uid": c["syncUid"],
            "parent_id": c["parentId"] if c["parentId"] in existing_ids else None,
            "lft": c["lft"],
            "rgt": c["rgt"],
            "level": c["level"],
            "last_level": c["lastLevel"],
            "path": c["path"],
            "path_array": c["pathArray"],
            "depth": c["depth"],
            "pos": c.get("pos"),
            "enabled": c["enabled"],
            "deleted": c["deleted"],
            "product_count_pim": c["productCountPim"],
            "created_at": c.get("createdAt"),
            "updated_at": c.get("updatedAt"),
        } for c in batch]
        
        supabase.table("catalogs").upsert(db_catalogs, on_conflict="id").execute()
        print(f"   ✅ {min(i + BATCH_SIZE, len(catalogs_sorted))}/{len(catalogs_sorted)}")
    
    print(f"✅ Загружено {len(catalogs_sorted)} каталогов\n")
    
    # 3. Получаем ID товаров из БД
    print("📦 Получение товаров из БД...")
    products_result = supabase.table("products").select("id").execute()
    existing_product_ids = {p["id"] for p in products_result.data}
    print(f"✅ Найдено {len(existing_product_ids)} товаров\n")
    
    # 4. Загружаем связи из PIM
    print("📥 Загрузка связей из PIM...")
    links_data = load_json(LINKS_JSON)
    links = links_data["links"]
    print(f"✅ Обработано {len(links)} связей из PIM\n")
    
    # 5. Создаем связи (products.id = PIM product.id)
    print("🔗 Создание связей товары ↔ каталоги...")
    product_catalogs = []
    skipped = 0
    
    for link in links:
        product_id = link["product_id"]  # ID из PIM
        
        # Проверяем, есть ли товар в БД
        if product_id in existing_product_ids:
            product_catalogs.append({
                "product_id": product_id,
                "catalog_id": link["catalog_id"],
                "is_primary": link["is_primary"],
                "sort_order": link["sort_order"],
            })
        else:
            skipped += 1
    
    print(f"   • Создано связей: {len(product_catalogs)}")
    print(f"   • Пропущено (товар не в БД): {skipped}\n")
    
    # 6. Загружаем связи батчами
    print("💾 Загрузка связей в БД...")
    for i in range(0, len(product_catalogs), BATCH_SIZE):
        batch = product_catalogs[i:i + BATCH_SIZE]
        supabase.table("product_catalogs").upsert(
            batch,
            on_conflict="product_id,catalog_id"
        ).execute()
        print(f"   ✅ {min(i + BATCH_SIZE, len(product_catalogs))}/{len(product_catalogs)}")
    
    print(f"\n✅ Загружено {len(product_catalogs)} связей")
    
    # 7. Статистика
    print("\n📊 СТАТИСТИКА:")
    result = supabase.table("product_catalogs").select("*", count="exact").execute()
    print(f"   • Всего связей в БД: {result.count}")
    
    primary = supabase.table("product_catalogs").select("*", count="exact").eq("is_primary", True).execute()
    print(f"   • Основных категорий: {primary.count}")
    
    print("\n✨ Готово! Товары связаны с каталогами.")


if __name__ == "__main__":
    main()

