#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обновляет поле id в таблице products из pim_product_id для товаров, где pim_product_id не NULL.

ВНИМАНИЕ: Обновление первичного ключа через API может быть проблематичным.
Рекомендуется использовать SQL запрос напрямую в базе данных.
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Отсутствуют SUPABASE_URL или SUPABASE_KEY")
        sys.exit(1)
    
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("📥 Проверка товаров с pim_product_id...")
    
    # Подсчитываем товары, которые нужно обновить
    response = (
        client.table("products")
        .select("id,pim_product_id", count="exact")
        .not_.is_("pim_product_id", "null")
        .execute()
    )
    
    total = response.count or 0
    print(f"✅ Найдено {total} товаров с pim_product_id")
    
    if total == 0:
        print("✅ Нет товаров для обновления")
        return
    
    print("\n" + "="*60)
    print("⚠️  ВНИМАНИЕ: Обновление первичного ключа через API ограничено")
    print("="*60)
    print("\n📋 Рекомендуется выполнить SQL запрос напрямую в базе данных:")
    print("\n   UPDATE products")
    print("   SET id = pim_product_id")
    print("   WHERE pim_product_id IS NOT NULL")
    print("     AND id != pim_product_id;")
    print("\n" + "="*60)
    
    # Показываем статистику
    response = (
        client.table("products")
        .select("id,pim_product_id")
        .not_.is_("pim_product_id", "null")
        .limit(10)
        .execute()
    )
    
    needs_update = [r for r in response.data if r.get("id") != r.get("pim_product_id")]
    
    if needs_update:
        print(f"\n📊 Примеры товаров, которые нужно обновить (первые 10):")
        for item in needs_update[:10]:
            print(f"   id={item['id']} -> должен быть id={item['pim_product_id']}")
    else:
        print("\n✅ Все товары уже синхронизированы (id == pim_product_id)")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"❌ Критическая ошибка: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
