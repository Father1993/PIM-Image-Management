#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка товаров в категории PIM через API
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

PIM_API_URL = os.getenv("PIM_API_URL")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")


def authenticate():
    """Авторизация в PIM API"""
    response = requests.post(
        f"{PIM_API_URL}/sign-in/",
        json={"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
    )
    response.raise_for_status()
    return response.json()["data"]["access"]["token"]


def get_products_in_category(token, catalog_id):
    """Получение товаров в категории через scroll API"""
    headers = {"Authorization": f"Bearer {token}"}
    products = []
    
    try:
        # Первый запрос - получаем scrollId
        url = f"{PIM_API_URL}/product/scroll"
        params = {"catalogId": catalog_id}
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("data"):
                products.extend(data["data"].get("products", []))
                scroll_id = data["data"].get("scrollId")
                
                # Продолжаем пока есть scroll_id
                while scroll_id and len(products) < 1000:  # Ограничение в 1000 товаров
                    params = {"scrollId": scroll_id, "catalogId": catalog_id}
                    response = requests.get(url, headers=headers, params=params, timeout=30)
                    
                    if response.status_code != 200:
                        break
                    
                    data = response.json()
                    if not data.get("success"):
                        break
                    
                    scroll_data = data.get("data", {})
                    new_products = scroll_data.get("products", [])
                    
                    if not new_products:
                        break
                    
                    products.extend(new_products)
                    scroll_id = scroll_data.get("scrollId")
        
        return products
    except Exception as e:
        print(f"Ошибка при получении товаров: {e}")
        return []


def main():
    if len(sys.argv) < 2:
        print("Использование: python check_category_products.py <catalog_id>")
        print("Пример: python check_category_products.py 778")
        sys.exit(1)
    
    catalog_id = int(sys.argv[1])
    
    print(f"🔐 Авторизация в PIM API...")
    token = authenticate()
    print("✅ Авторизация успешна\n")
    
    print(f"📦 Получение товаров из категории ID={catalog_id}...")
    products = get_products_in_category(token, catalog_id)
    
    print(f"\n📊 Найдено товаров: {len(products)}\n")
    
    if products:
        print("🔍 Последние 10 товаров:")
        for i, product in enumerate(products[-10:], 1):
            print(f"\n{i}. ID: {product.get('id')}")
            print(f"   Название: {product.get('header', 'N/A')}")
            print(f"   Артикул: {product.get('articul', 'N/A')}")
            print(f"   Категория ID: {product.get('catalogId', 'N/A')}")
            print(f"   Категория: {product.get('catalogHeader', 'N/A')}")
            print(f"   Активен: {product.get('enabled', 'N/A')}")
            print(f"   Удален: {product.get('deleted', 'N/A')}")
            print(f"   Создан: {product.get('createdAt', 'N/A')}")
    else:
        print("⚠️  В категории нет товаров")


if __name__ == "__main__":
    main()

