#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для сбора ID признаков матрицы из PIM системы
Делает запросы к product-group/{id} от 1 до 100 и сохраняет результаты в JSON
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
OUTPUT_FILE = "data/matrix_groups.json"


async def get_pim_token(session):
    """Получить токен авторизации PIM API"""
    auth_data = {"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
    async with session.post(f"{PIM_API_URL}/sign-in/", json=auth_data) as response:
        if response.status == 200:
            data = await response.json()
            if data.get("success") and data.get("data", {}).get("access", {}).get("token"):
                return data["data"]["access"]["token"]
    return None


async def fetch_group(session, token, group_id):
    """Получить информацию о группе по ID"""
    headers = {"Authorization": f"Bearer {token}"}
    async with session.get(f"{PIM_API_URL}/product-group/{group_id}", headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            if data.get("success") and data.get("data"):
                return data["data"]
    return None


async def main():
    try:
        async with aiohttp.ClientSession() as session:
            print("🔐 Авторизация в PIM API...")
            token = await get_pim_token(session)
            if not token:
                print("❌ Ошибка авторизации в PIM")
                return
            print("✅ Авторизация успешна\n")
            
            print("📊 Сбор признаков матрицы (ID 1-100)...")
            groups = {}
            found_count = 0
            
            for group_id in range(1, 101):
                group_data = await fetch_group(session, token, group_id)
                if group_data:
                    header = group_data.get("header", "").strip()
                    if header:
                        groups[header] = {
                            "id": group_data.get("id"),
                            "header": header,
                            "syncUid": group_data.get("syncUid"),
                            "enabled": group_data.get("enabled", True),
                            "deleted": group_data.get("deleted", False)
                        }
                        found_count += 1
                        print(f"✅ ID {group_id}: {header}")
                
                # Небольшая задержка чтобы не перегружать API
                if group_id % 10 == 0:
                    await asyncio.sleep(0.1)
            
            if not groups:
                print("❌ Признаки матрицы не найдены")
                return
            
            # Сохраняем результаты
            os.makedirs("data", exist_ok=True)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(groups, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 Данные сохранены в {OUTPUT_FILE}")
            print(f"📊 Найдено признаков матрицы: {found_count}")
            print(f"\n📋 Список найденных признаков:")
            for header in sorted(groups.keys()):
                print(f"   - {header} (ID: {groups[header]['id']})")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

