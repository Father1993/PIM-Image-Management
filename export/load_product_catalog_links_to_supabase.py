#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Загрузка связей товаров с каталогами из JSON в Supabase.
Предварительно нужно запустить export_product_catalog_links.py
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
LINKS_JSON = os.getenv("PIM_PRODUCT_CATALOG_OUTPUT", "data/product_catalog_links.json")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "500"))


def ensure_env() -> None:
    """Проверка наличия обязательных переменных окружения."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Укажите SUPABASE_URL и SUPABASE_KEY в .env")
    if not os.path.exists(LINKS_JSON):
        raise RuntimeError(f"Файл {LINKS_JSON} не найден. Сначала запустите export_product_catalog_links.py")


def load_links_data() -> dict[str, Any]:
    """Загрузка данных связей из JSON."""
    with open(LINKS_JSON, "r", encoding="utf-8") as fh:
        return json.load(fh)


def prepare_link_for_db(link: dict) -> dict:
    """Подготовка данных связи для вставки в БД."""
    return {
        "product_id": link["product_id"],
        "catalog_id": link["catalog_id"],
        "is_primary": link["is_primary"],
        "sort_order": link["sort_order"],
        "created_at": datetime.utcnow().isoformat(),
    }


async def clear_existing_links(supabase: Client) -> None:
    """Очистка существующих связей (опционально)."""
    print("🗑️  Очистка существующих связей товаров с каталогами...")
    
    try:
        supabase.table("product_catalogs").delete().neq("product_id", 0).execute()
        print("✅ Существующие связи очищены")
    except Exception as e:
        print(f"⚠️  Ошибка при очистке связей: {e}")


async def insert_links_batch(supabase: Client, links: list[dict]) -> None:
    """Вставка связей батчами."""
    total = len(links)
    success_count = 0
    error_count = 0
    
    print(f"\n📥 Загрузка {total} связей в Supabase...")
    
    for i in range(0, total, BATCH_SIZE):
        batch = links[i:i + BATCH_SIZE]
        try:
            # Используем upsert для обновления существующих записей
            supabase.table("product_catalogs").upsert(
                batch,
                on_conflict="product_id,catalog_id"
            ).execute()
            
            success_count += len(batch)
            print(f"✅ Загружено {min(i + BATCH_SIZE, total)}/{total} связей")
            
        except Exception as e:
            error_count += len(batch)
            print(f"❌ Ошибка при загрузке связей {i}-{i + BATCH_SIZE}: {e}")
            
            # Пробуем вставить по одной для определения проблемных записей
            for link in batch:
                try:
                    supabase.table("product_catalogs").upsert(
                        [link],
                        on_conflict="product_id,catalog_id"
                    ).execute()
                    success_count += 1
                    error_count -= 1
                except Exception as inner_e:
                    print(f"   ❌ Проблемная связь товар={link['product_id']}, каталог={link['catalog_id']}: {inner_e}")
    
    print(f"\n📊 Результат загрузки:")
    print(f"   • Успешно: {success_count}")
    print(f"   • Ошибок: {error_count}")


async def verify_links(supabase: Client, expected_count: int) -> None:
    """Проверка корректности загруженных связей."""
    print("\n🔍 Проверка загруженных связей...")
    
    try:
        # Общее количество связей
        result = supabase.table("product_catalogs").select("product_id", count="exact").execute()
        actual_count = result.count
        
        print(f"   • Загружено связей: {actual_count}/{expected_count}")
        
        if actual_count == expected_count:
            print("   ✅ Все связи загружены успешно")
        else:
            print(f"   ⚠️  Не все связи загружены ({actual_count} из {expected_count})")
        
        # Количество основных категорий
        primary_result = supabase.table("product_catalogs").select(
            "product_id",
            count="exact"
        ).eq("is_primary", True).execute()
        print(f"   • Основных категорий: {primary_result.count}")
        
        # Количество дополнительных категорий
        additional_result = supabase.table("product_catalogs").select(
            "product_id",
            count="exact"
        ).eq("is_primary", False).execute()
        print(f"   • Дополнительных категорий: {additional_result.count}")
        
        # Топ-5 каталогов по количеству товаров
        print("\n📊 Топ-5 каталогов по количеству товаров:")
        
        # Группируем и считаем через SQL
        top_catalogs = supabase.table("product_catalogs").select(
            "catalog_id",
            count="exact"
        ).limit(5).execute()
        
        # Простой подсчет через Python (если RPC недоступен)
        all_links = supabase.table("product_catalogs").select("catalog_id").execute()
        catalog_counts: dict[int, int] = {}
        for link in all_links.data:
            cat_id = link["catalog_id"]
            catalog_counts[cat_id] = catalog_counts.get(cat_id, 0) + 1
        
        top_5 = sorted(catalog_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        for idx, (cat_id, count) in enumerate(top_5, 1):
            # Получаем название каталога
            cat_result = supabase.table("catalogs").select("header").eq("id", cat_id).execute()
            cat_name = cat_result.data[0]["header"] if cat_result.data else "Неизвестно"
            print(f"   {idx}. Каталог #{cat_id} ({cat_name}): {count} товаров")
        
    except Exception as e:
        print(f"⚠️  Ошибка при проверке данных: {e}")


async def update_catalog_counts(supabase: Client) -> None:
    """Обновление счетчиков товаров в каталогах."""
    print("\n🔄 Обновление счетчиков товаров в каталогах...")
    
    try:
        # Получаем все связи
        links_result = supabase.table("product_catalogs").select("catalog_id").execute()
        
        # Считаем товары по каталогам
        catalog_counts: dict[int, int] = {}
        for link in links_result.data:
            cat_id = link["catalog_id"]
            catalog_counts[cat_id] = catalog_counts.get(cat_id, 0) + 1
        
        # Обновляем счетчики
        updated = 0
        for cat_id, count in catalog_counts.items():
            try:
                supabase.table("catalogs").update({
                    "product_count": count
                }).eq("id", cat_id).execute()
                updated += 1
            except Exception as e:
                print(f"   ⚠️  Ошибка обновления счетчика для каталога {cat_id}: {e}")
        
        print(f"✅ Обновлено счетчиков: {updated}/{len(catalog_counts)}")
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении счетчиков: {e}")


async def main():
    """Основная функция."""
    ensure_env()
    
    # Загружаем данные из JSON
    print("📂 Загрузка данных из JSON...")
    links_data = load_links_data()
    links = links_data["links"]
    statistics = links_data["statistics"]
    
    print(f"✅ Загружено {len(links)} связей из JSON")
    print(f"📊 Статистика:")
    print(f"   • Всего товаров: {statistics['total_products']}")
    print(f"   • Всего связей: {statistics['total_links']}")
    print(f"   • Основных категорий: {statistics['primary_links']}")
    print(f"   • Дополнительных категорий: {statistics['additional_links']}")
    
    # Подключаемся к Supabase
    print("\n🔌 Подключение к Supabase...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Подключение установлено")
    
    # Опционально: очищаем существующие связи
    clear_data = input("\n❓ Очистить существующие связи? (y/N): ").strip().lower()
    if clear_data == "y":
        await clear_existing_links(supabase)
    
    # Подготавливаем данные для вставки
    print("\n🔧 Подготовка данных...")
    db_links = [prepare_link_for_db(link) for link in links]
    
    # Загружаем связи
    await insert_links_batch(supabase, db_links)
    
    # Проверяем результат
    await verify_links(supabase, len(links))
    
    # Обновляем счетчики в каталогах
    update_counts = input("\n❓ Обновить счетчики товаров в каталогах? (Y/n): ").strip().lower()
    if update_counts != "n":
        await update_catalog_counts(supabase)
    
    print("\n✨ Загрузка завершена!")


if __name__ == "__main__":
    asyncio.run(main())

