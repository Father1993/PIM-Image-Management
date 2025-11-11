#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка товаров в категории через Elastic Search API
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


def get_products_elastic(token, catalog_id, page=0, size=10):
    """Получение товаров через Elastic Search API"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        url = f"{PIM_API_URL}/product/elastic/{catalog_id}/page/{page}/{size}/header/asc/"
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("data"):
                return data["data"]
        else:
            print(f"Ошибка HTTP {response.status_code}: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"Ошибка при получении товаров: {e}")
        return None


def main():
    if len(sys.argv) < 2:
        print("Использование: python check_category_elastic.py <catalog_id> [page] [size]")
        print("Пример: python check_category_elastic.py 778 0 10")
        sys.exit(1)
    
    catalog_id = int(sys.argv[1])
    page = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    size = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    
    print(f"🔐 Авторизация в PIM API...")
    token = authenticate()
    print("✅ Авторизация успешна\n")
    
    print(f"📦 Получение товаров из категории ID={catalog_id} (страница {page}, размер {size})...")
    data = get_products_elastic(token, catalog_id, page, size)
    
    if data:
        content = data.get("content", [])
        total_elements = data.get("totalElements", 0)
        total_pages = data.get("totalPages", 0)
        
        print(f"\n📊 Всего товаров: {total_elements}")
        print(f"📄 Всего страниц: {total_pages}")
        print(f"📄 На текущей странице: {len(content)}\n")
        
        if content:
            print(f"🔍 Товары на странице {page}:")
            for i, product in enumerate(content, 1):
                print(f"\n{i}. ID: {product.get('id')}")
                print(f"   Название: {product.get('header', 'N/A')[:60]}...")
                print(f"   Артикул: {product.get('articul', 'N/A')}")
                print(f"   catalogId: {product.get('catalogId', 'N/A')}")
                print(f"   Категория: {product.get('catalogHeader', 'N/A')}")
                print(f"   Активен: {product.get('enabled', 'N/A')}")
                print(f"   Удален: {product.get('deleted', 'N/A')}")
        else:
            print("⚠️  На текущей странице нет товаров")
    else:
        print("\n❌ Не удалось получить данные")


if __name__ == "__main__":
    main()

