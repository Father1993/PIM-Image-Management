#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Асинхронный скрипт для удаления проблемных товаров из таблиц onec_catalog и new_onec_products
по кодам из Excel файла
"""

import os
import pandas as pd
import asyncio
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


async def delete_from_table(client, table_name, codes, batch_size=100):
    """Удаление товаров из таблицы пакетами"""
    deleted_count = 0
    
    for i in range(0, len(codes), batch_size):
        batch = codes[i:i + batch_size]
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.table(table_name)
                .delete()
                .in_("code_1c", batch)
                .execute()
        )
        
        deleted_count += len(response.data) if response.data else 0
        print(f"   Удалено {deleted_count}/{len(codes)} из {table_name}")
    
    return deleted_count


async def verify_deletion(client, table_name, codes):
    """Проверка, что товары удалены"""
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.table(table_name)
            .select("code_1c")
            .in_("code_1c", codes)
            .execute()
    )
    
    remaining = [item.get("code_1c") for item in (response.data or [])]
    return remaining


async def main():
    excel_file = "problem_products_ya_20251128_161622.xlsx"
    
    try:
        # Читаем Excel файл
        print(f"📂 Читаю файл {excel_file}...")
        df = pd.read_excel(excel_file)
        
        # Извлекаем code_1c
        codes = [str(code).strip() for code in df["Код 1С"].dropna() if str(code).strip()]
        print(f"✅ Найдено {len(codes)} кодов для удаления")
        
        if not codes:
            print("❌ Нет кодов для удаления")
            return
        
        # Подключение к Supabase
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Подключение к Supabase установлено")
        
        # Удаляем из onec_catalog
        print(f"\n🗑️  Удаление из таблицы onec_catalog...")
        deleted_onec = await delete_from_table(client, "onec_catalog", codes)
        
        # Удаляем из new_onec_products
        print(f"\n🗑️  Удаление из таблицы new_onec_products...")
        deleted_new = await delete_from_table(client, "new_onec_products", codes)
        
        print(f"\n✅ Удалено из onec_catalog: {deleted_onec}")
        print(f"✅ Удалено из new_onec_products: {deleted_new}")
        
        # Проверяем удаление
        print(f"\n🔍 Проверка удаления...")
        remaining_onec = await verify_deletion(client, "onec_catalog", codes)
        remaining_new = await verify_deletion(client, "new_onec_products", codes)
        
        if remaining_onec:
            print(f"⚠️  В onec_catalog осталось {len(remaining_onec)} товаров: {remaining_onec[:5]}")
        else:
            print(f"✅ В onec_catalog товаров не найдено")
        
        if remaining_new:
            print(f"⚠️  В new_onec_products осталось {len(remaining_new)} товаров: {remaining_new[:5]}")
        else:
            print(f"✅ В new_onec_products товаров не найдено")
        
        print(f"\n🎉 Готово!")
        
    except FileNotFoundError:
        print(f"❌ Файл {excel_file} не найден")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

