#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для поиска товаров в PIM без назначенного признака матрицы.
Сохраняет ID товаров в JSON файл.
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

PIM_API_URL = (os.getenv("PIM_API_URL") or "").rstrip("/")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")
CATALOG_ID = int(os.getenv("PIM_CATALOG_ID", "22"))
OUTPUT_FILE = f"products_without_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


async def get_pim_token(session):
    """Получить токен авторизации PIM"""
    payload = {"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
    async with session.post(f"{PIM_API_URL}/sign-in/", json=payload) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Ошибка авторизации: {resp.status}")
        data = await resp.json()
        token = data.get("data", {}).get("access", {}).get("token")
        if not token:
            raise RuntimeError("Не удалось получить токен")
        return token


def has_no_matrix(product):
    """Проверить, есть ли у товара признак матрицы"""
    product_group_id = product.get("productGroupId")
    product_group = product.get("productGroup")
    
    # Проверяем оба поля: если productGroupId пустой/null И productGroup null
    if product_group_id is None or product_group_id == "":
        if product_group is None:
            return True
    return False


async def find_products_without_matrix(session, token):
    """Найти все товары без признака матрицы через scroll API"""
    headers = {"Authorization": f"Bearer {token}"}
    products_without_matrix = []
    scroll_id = None
    page = 0
    
    print("📥 Поиск товаров без признака матрицы...")
    
    while True:
        page += 1
        params = {"catalogId": CATALOG_ID}
        if scroll_id:
            params["scrollId"] = scroll_id
        
        async with session.get(f"{PIM_API_URL}/product/scroll", headers=headers, params=params) as resp:
            if resp.status != 200:
                print(f"❌ Ошибка HTTP {resp.status} на странице {page}")
                break
            
            data = await resp.json()
            if not data.get("success"):
                print(f"❌ Ошибка API: {data.get('message', 'Unknown error')}")
                break
            
            scroll_data = data.get("data", {})
            products = scroll_data.get("products") or scroll_data.get("productElasticDtos") or []
            
            if not products:
                break
            
            # Фильтруем товары без признака матрицы
            for product in products:
                if has_no_matrix(product):
                    products_without_matrix.append({
                        "id": product.get("id"),
                        "header": product.get("header"),
                        "articul": product.get("articul"),
                        "productGroupId": product.get("productGroupId"),
                        "productGroup": product.get("productGroup")
                    })
            
            print(f"📄 Страница {page}: проверено {len(products)} товаров, найдено без матрицы: {len(products_without_matrix)}")
            
            scroll_id = scroll_data.get("scrollId")
            if not scroll_id:
                break
    
    return products_without_matrix


async def main():
    async with aiohttp.ClientSession() as session:
        print("🔐 Авторизация в PIM API...")
        token = await get_pim_token(session)
        print("✅ Авторизация успешна\n")
        
        products = await find_products_without_matrix(session, token)
        
        if not products:
            print("✅ Товаров без признака матрицы не найдено")
            return
        
        # Сохраняем результат
        result = {
            "total": len(products),
            "found_at": datetime.now().isoformat(),
            "products": products
        }
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Найдено {len(products)} товаров без признака матрицы")
        print(f"💾 Результаты сохранены в {OUTPUT_FILE}")
        
        # Выводим первые 10 ID для примера
        if products:
            print(f"\n📋 Примеры ID (первые 10):")
            for p in products[:10]:
                print(f"   - ID: {p['id']}, Название: {p.get('header', 'N/A')[:50]}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"❌ Критическая ошибка: {exc}")
        import traceback
        traceback.print_exc()

