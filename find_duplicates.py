#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для поиска дубликатов товаров в PIM по артикулу
Помогает найти товары, которые были созданы несколько раз
"""

import os
import requests
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

PIM_API_URL = os.getenv("PRODUCT_BASE")
PIM_LOGIN = os.getenv("LOGIN_TEST")
PIM_PASSWORD = os.getenv("PASSWORD_TEST")
CATALOG_1C_ID = 22


def authenticate():
    """Авторизация в PIM API"""
    response = requests.post(
        f"{PIM_API_URL}/sign-in/",
        json={"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
    )
    response.raise_for_status()
    return response.json()["data"]["access"]["token"]


def find_duplicates(token, catalog_id=CATALOG_1C_ID):
    """Поиск дубликатов товаров по артикулу"""
    print("🔍 Поиск дубликатов товаров в PIM...")
    print("⏳ Это может занять некоторое время...\n")
    
    headers = {"Authorization": f"Bearer {token}"}
    articul_map = defaultdict(list)  # артикул -> список товаров
    
    try:
        # Первый запрос - получаем scrollId
        url = f"{PIM_API_URL}/product/scroll"
        params = {"catalogId": catalog_id}
        response = requests.get(url, headers=headers, params=params, timeout=60)
        
        if response.status_code != 200:
            print(f"❌ Ошибка запроса: {response.status_code}")
            return
        
        data = response.json()
        if not data.get("success"):
            print(f"❌ Ошибка: {data}")
            return
        
        scroll_id = data["data"].get("scrollId")
        products = data["data"].get("products", [])
        total = data["data"].get("total", 0)
        
        print(f"📊 Всего товаров в каталоге: {total}")
        print(f"📦 Обработано: {len(products)}", end="", flush=True)
        
        # Обрабатываем первую порцию
        for product in products:
            articul = str(product.get("articul", "")).strip()
            if articul:
                articul_map[articul].append({
                    "id": product.get("id"),
                    "header": product.get("header", "N/A"),
                    "articul": articul
                })
        
        # Продолжаем поиск по scroll
        page = 1
        while scroll_id:
            url = f"{PIM_API_URL}/product/scroll"
            params = {"scrollId": scroll_id, "catalogId": catalog_id}
            response = requests.get(url, headers=headers, params=params, timeout=60)
            
            if response.status_code != 200:
                break
            
            data = response.json()
            if not data.get("success"):
                break
            
            scroll_data = data.get("data", {})
            products = scroll_data.get("products", [])
            
            if not products:
                break
            
            for product in products:
                articul = str(product.get("articul", "")).strip()
                if articul:
                    articul_map[articul].append({
                        "id": product.get("id"),
                        "header": product.get("header", "N/A"),
                        "articul": articul
                    })
            
            page += 1
            print(f"\r📦 Обработано: {len(articul_map)} уникальных артикулов", end="", flush=True)
            scroll_id = scroll_data.get("scrollId")
        
        print("\n")
        
        # Находим дубликаты
        duplicates = {k: v for k, v in articul_map.items() if len(v) > 1}
        
        if duplicates:
            print(f"⚠️  Найдено {len(duplicates)} артикулов с дубликатами:\n")
            for articul, products_list in sorted(duplicates.items()):
                print(f"🔢 Артикул: {articul} ({len(products_list)} дубликатов)")
                for p in products_list:
                    print(f"   - ID: {p['id']}, Название: {p['header'][:60]}")
                print()
        else:
            print("✅ Дубликатов не найдено!")
        
        return duplicates
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


def main():
    required_vars = ["PRODUCT_BASE", "LOGIN_TEST", "PASSWORD_TEST"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"❌ Отсутствуют переменные окружения: {', '.join(missing)}")
        return
    
    print("🔐 Авторизация в PIM API...")
    token = authenticate()
    print("✅ Авторизация успешна\n")
    
    duplicates = find_duplicates(token)
    
    if duplicates:
        print(f"\n📊 Итого: {len(duplicates)} артикулов с дубликатами")
        total_duplicates = sum(len(v) - 1 for v in duplicates.values())
        print(f"📊 Всего лишних товаров: {total_duplicates}")


if __name__ == "__main__":
    main()

