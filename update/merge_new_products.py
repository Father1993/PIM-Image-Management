#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Объединяет данные из new_onec_products в products.
Переносит товары с правильным маппингом полей и объединением категорий.
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BATCH_SIZE = 500


def build_product_group(groups):
    """Объединяет group1-group10 в строку product_group с разделителем /"""
    parts = [g.strip() for g in groups if g and str(g).strip()]
    return " / ".join(parts) if parts else None


def map_product(new_product):
    """Маппинг полей из new_onec_products в products"""
    groups = [
        new_product.get("group1"),
        new_product.get("group2"),
        new_product.get("group3"),
        new_product.get("group4"),
        new_product.get("group5"),
        new_product.get("group6"),
        new_product.get("group7"),
        new_product.get("group8"),
        new_product.get("group9"),
        new_product.get("group10"),
    ]
    
    return {
        "product_name": new_product.get("product_name"),
        "article": new_product.get("article"),
        "code_1c": new_product.get("code_1c"),
        "barcode": new_product.get("barcode"),
        "provider": new_product.get("provider"),
        "brend": new_product.get("brand"),  # brand -> brend
        "mass": new_product.get("weight"),  # weight -> mass
        "volume": new_product.get("volume"),
        "length": new_product.get("length"),
        "matrix": new_product.get("matrix"),
        "product_group": build_product_group(groups),
        "pim_product_id": new_product.get("pim_product_id"),
        "image_optimized_url": new_product.get("image_optimized_url"),
        "updated_at_image_optimized": new_product.get("updated_at_image_optimized"),
        "is_optimized": new_product.get("is_optimized"),
    }


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Отсутствуют SUPABASE_URL или SUPABASE_KEY")
        sys.exit(1)
    
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("📥 Загрузка товаров из new_onec_products...")
    new_products = []
    offset = 0
    
    while True:
        response = (
            client.table("new_onec_products")
            .select("*")
            .range(offset, offset + BATCH_SIZE - 1)
            .execute()
        )
        batch = response.data or []
        if not batch:
            break
        new_products.extend(batch)
        offset += BATCH_SIZE
    
    print(f"✅ Загружено {len(new_products)} товаров из new_onec_products")
    
    if not new_products:
        print("✅ Нет товаров для обработки")
        return
    
    print("📋 Подготовка данных...")
    to_insert = []
    skipped = 0
    
    for new_product in new_products:
        mapped = map_product(new_product)
        pim_id = mapped.get("pim_product_id")
        
        if pim_id:
            # Создаем новый товар с PIM ID
            mapped["id"] = pim_id
            mapped["is_new_product"] = True
            to_insert.append(mapped)
        else:
            # Товар без PIM ID - пропускаем (нельзя создать без id в products)
            skipped += 1
    
    print(f"✅ К вставке: {len(to_insert)}, пропущено: {skipped}")
    
    # Дедуплицируем to_insert по id (оставляем последнее значение)
    if to_insert:
        unique_inserts = {}
        for item in to_insert:
            unique_inserts[item["id"]] = item
        to_insert = list(unique_inserts.values())
        print(f"🔍 После дедупликации: {len(to_insert)} уникальных товаров для вставки")
    
    # Вставляем новые
    if to_insert:
        print(f"💾 Вставка {len(to_insert)} новых товаров...")
        for i in range(0, len(to_insert), BATCH_SIZE):
            batch = to_insert[i:i + BATCH_SIZE]
            client.table("products").insert(batch).execute()
            print(f"✅ Вставлено: {min(i + BATCH_SIZE, len(to_insert))}/{len(to_insert)}")
    
    print(f"\n🎉 Готово! Вставлено: {len(to_insert)}, Пропущено: {skipped}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"❌ Критическая ошибка: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

