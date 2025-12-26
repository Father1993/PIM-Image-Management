#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Загрузка структуры каталогов из JSON в Supabase.
Предварительно нужно запустить export_catalog_structure.py
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
CATALOG_JSON = os.getenv("PIM_CATALOG_OUTPUT", "data/catalog_structure.json")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))


def ensure_env() -> None:
    """Проверка наличия обязательных переменных окружения."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Укажите SUPABASE_URL и SUPABASE_KEY в .env")
    if not os.path.exists(CATALOG_JSON):
        raise RuntimeError(f"Файл {CATALOG_JSON} не найден. Сначала запустите export_catalog_structure.py")


def load_catalog_data() -> dict[str, Any]:
    """Загрузка данных каталога из JSON."""
    with open(CATALOG_JSON, "r", encoding="utf-8") as fh:
        return json.load(fh)


def prepare_catalog_for_db(catalog: dict) -> dict:
    """Подготовка данных каталога для вставки в БД."""
    return {
        "id": catalog["id"],
        "header": catalog["header"],
        "sync_uid": catalog["syncUid"],
        "parent_id": catalog["parentId"],
        "lft": catalog["lft"],
        "rgt": catalog["rgt"],
        "level": catalog["level"],
        "last_level": catalog["lastLevel"],
        "path": catalog["path"],
        "path_array": catalog["pathArray"],
        "depth": catalog["depth"],
        "pos": catalog.get("pos"),
        "enabled": catalog["enabled"],
        "deleted": catalog["deleted"],
        "product_count": catalog["productCount"],
        "product_count_additional": catalog["productCountAdditional"],
        "product_count_pim": catalog["productCountPim"],
        "product_count_pim_additional": catalog["productCountPimAdditional"],
        "ht_head": catalog.get("htHead"),
        "ht_desc": catalog.get("htDesc"),
        "ht_keywords": catalog.get("htKeywords"),
        "content": catalog.get("content"),
        "created_at": catalog.get("createdAt"),
        "updated_at": catalog.get("updatedAt"),
        "synced_at": datetime.utcnow().isoformat(),
        "metadata": {
            "has_children": catalog["hasChildren"],
            "children_count": catalog["childrenCount"],
            "picture": catalog.get("picture"),
            "icon": catalog.get("icon"),
            "channels": catalog.get("channels", []),
        }
    }


def prepare_terms_for_db(catalog: dict) -> list[dict]:
    """Подготовка синонимов каталога для вставки в БД."""
    terms = []
    for term in catalog.get("terms", []):
        if isinstance(term, dict) and term.get("header"):
            terms.append({
                "catalog_id": catalog["id"],
                "term": term["header"]
            })
    return terms


async def clear_existing_data(supabase: Client) -> None:
    """Очистка существующих данных (опционально)."""
    print("🗑️  Очистка существующих данных...")
    
    try:
        # Удаляем в правильном порядке из-за foreign keys
        supabase.table("catalog_terms").delete().neq("id", 0).execute()
        supabase.table("catalog_channels").delete().neq("id", 0).execute()
        supabase.table("product_catalogs").delete().neq("product_id", 0).execute()
        supabase.table("catalogs").delete().neq("id", 0).execute()
        print("✅ Существующие данные очищены")
    except Exception as e:
        print(f"⚠️  Ошибка при очистке данных: {e}")
        print("   Возможно, таблицы еще не созданы. Продолжаем...")


async def insert_catalogs_batch(supabase: Client, catalogs: list[dict]) -> None:
    """Вставка каталогов батчами."""
    total = len(catalogs)
    
    for i in range(0, total, BATCH_SIZE):
        batch = catalogs[i:i + BATCH_SIZE]
        try:
            # Используем upsert для обновления существующих записей
            supabase.table("catalogs").upsert(batch, on_conflict="id").execute()
            print(f"✅ Загружено {min(i + BATCH_SIZE, total)}/{total} каталогов")
        except Exception as e:
            print(f"❌ Ошибка при загрузке каталогов {i}-{i + BATCH_SIZE}: {e}")
            # Пробуем вставить по одному для определения проблемной записи
            for catalog in batch:
                try:
                    supabase.table("catalogs").upsert([catalog], on_conflict="id").execute()
                except Exception as inner_e:
                    print(f"   ❌ Проблемный каталог ID {catalog['id']}: {inner_e}")


async def insert_terms_batch(supabase: Client, all_terms: list[dict]) -> None:
    """Вставка синонимов батчами."""
    if not all_terms:
        print("ℹ️  Синонимы отсутствуют")
        return
    
    total = len(all_terms)
    print(f"\n📝 Загрузка {total} синонимов...")
    
    for i in range(0, total, BATCH_SIZE):
        batch = all_terms[i:i + BATCH_SIZE]
        try:
            supabase.table("catalog_terms").upsert(batch, on_conflict="catalog_id,term").execute()
            print(f"✅ Загружено {min(i + BATCH_SIZE, total)}/{total} синонимов")
        except Exception as e:
            print(f"❌ Ошибка при загрузке синонимов {i}-{i + BATCH_SIZE}: {e}")


async def verify_data(supabase: Client, expected_count: int) -> None:
    """Проверка корректности загруженных данных."""
    print("\n🔍 Проверка загруженных данных...")
    
    try:
        # Проверяем количество каталогов
        result = supabase.table("catalogs").select("id", count="exact").execute()
        actual_count = result.count
        
        print(f"   • Загружено каталогов: {actual_count}/{expected_count}")
        
        if actual_count == expected_count:
            print("   ✅ Все каталоги загружены успешно")
        else:
            print(f"   ⚠️  Не все каталоги загружены ({actual_count} из {expected_count})")
        
        # Проверяем распределение по уровням
        levels_result = supabase.rpc("count_by_level").execute() if hasattr(supabase, "rpc") else None
        
        # Проверяем конечные каталоги
        leaf_result = supabase.table("catalogs").select("id", count="exact").eq("last_level", True).execute()
        print(f"   • Конечных каталогов: {leaf_result.count}")
        
        # Проверяем активные каталоги
        active_result = supabase.table("catalogs").select("id", count="exact").eq("enabled", True).eq("deleted", False).execute()
        print(f"   • Активных каталогов: {active_result.count}")
        
    except Exception as e:
        print(f"⚠️  Ошибка при проверке данных: {e}")


async def main():
    """Основная функция."""
    ensure_env()
    
    # Загружаем данные из JSON
    print("📂 Загрузка данных из JSON...")
    catalog_data = load_catalog_data()
    catalogs = catalog_data["catalogs"]
    statistics = catalog_data["statistics"]
    
    print(f"✅ Загружено {len(catalogs)} каталогов из JSON")
    print(f"📊 Статистика:")
    print(f"   • Всего каталогов: {statistics['total_catalogs']}")
    print(f"   • Максимальная глубина: {statistics['max_depth']}")
    print(f"   • Всего товаров: {statistics['total_products']}")
    
    # Подключаемся к Supabase
    print("\n🔌 Подключение к Supabase...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Подключение установлено")
    
    # Опционально: очищаем существующие данные
    clear_data = input("\n❓ Очистить существующие данные? (y/N): ").strip().lower()
    if clear_data == "y":
        await clear_existing_data(supabase)
    
    # Подготавливаем данные для вставки
    print("\n🔧 Подготовка данных...")
    db_catalogs = [prepare_catalog_for_db(cat) for cat in catalogs]
    
    all_terms = []
    for catalog in catalogs:
        all_terms.extend(prepare_terms_for_db(catalog))
    
    # Загружаем каталоги
    print(f"\n📥 Загрузка {len(db_catalogs)} каталогов в Supabase...")
    await insert_catalogs_batch(supabase, db_catalogs)
    
    # Загружаем синонимы
    if all_terms:
        await insert_terms_batch(supabase, all_terms)
    
    # Проверяем результат
    await verify_data(supabase, len(catalogs))
    
    print("\n✨ Загрузка завершена!")


if __name__ == "__main__":
    asyncio.run(main())

