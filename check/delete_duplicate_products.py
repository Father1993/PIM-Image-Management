#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для удаления дубликатов товаров из PIM
Удаляет товары по ID из файла duplicate_ids_for_deletion.json
"""

import os
import json
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

PIM_API_URL = os.getenv("PIM_API_URL")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")


async def get_pim_token(session):
    """Получить токен авторизации PIM API"""
    auth_data = {"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
    async with session.post(f"{PIM_API_URL}/sign-in/", json=auth_data) as response:
        if response.status == 200:
            data = await response.json()
            if data.get("success") and data.get("data", {}).get("access", {}).get("token"):
                return data["data"]["access"]["token"]
    return None


async def delete_product(session, token, product_id):
    """Удаление товара по ID (soft delete)"""
    headers = {"Authorization": f"Bearer {token}"}
    async with session.delete(f"{PIM_API_URL}/product/{product_id}", headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            return data.get("success", False)
        return False


async def main():
    try:
        # Загружаем ID для удаления
        print("📂 Загрузка ID из duplicate_ids_for_deletion.json...")
        with open("duplicate_ids_for_deletion.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        ids_to_delete = data.get("ids", [])
        if not ids_to_delete:
            print("❌ Нет ID для удаления")
            return
        
        print(f"✅ Найдено {len(ids_to_delete)} товаров для удаления\n")
        
        async with aiohttp.ClientSession() as session:
            print("🔐 Авторизация в PIM API...")
            token = await get_pim_token(session)
            if not token:
                print("❌ Ошибка авторизации в PIM")
                return
            print("✅ Авторизация успешна\n")
            
            success = 0
            failed = 0
            
            print("🗑️  Начинаем удаление дубликатов...\n")
            
            for idx, product_id in enumerate(ids_to_delete, 1):
                if await delete_product(session, token, product_id):
                    success += 1
                    print(f"✅ [{idx}/{len(ids_to_delete)}] Удален товар ID: {product_id}")
                else:
                    failed += 1
                    print(f"❌ [{idx}/{len(ids_to_delete)}] Ошибка удаления товара ID: {product_id}")
            
            print(f"\n🎉 Завершено! Удалено: {success}, Ошибок: {failed}, Всего: {len(ids_to_delete)}")
    
    except FileNotFoundError:
        print("❌ Файл duplicate_ids_for_deletion.json не найден")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

