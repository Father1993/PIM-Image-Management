#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка товара в PIM по ID
"""

import os
import sys
import requests
import json
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


def get_product(token, product_id):
    """Получение товара по ID"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(
            f"{PIM_API_URL}/product/{product_id}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("data"):
                return data["data"]
        elif response.status_code == 404:
            return None
        else:
            print(f"Ошибка HTTP {response.status_code}: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"Ошибка при получении товара: {e}")
        return None


def main():
    if len(sys.argv) < 2:
        print("Использование: python check_product_by_id.py <product_id>")
        print("Пример: python check_product_by_id.py 28157")
        sys.exit(1)
    
    product_id = int(sys.argv[1])
    
    print(f"🔐 Авторизация в PIM API...")
    token = authenticate()
    print("✅ Авторизация успешна\n")
    
    print(f"📦 Получение товара ID={product_id}...")
    product = get_product(token, product_id)
    
    if product:
        print(f"\n✅ Товар найден!\n")
        print(f"ID: {product.get('id')}")
        print(f"Название: {product.get('header', 'N/A')}")
        print(f"Артикул: {product.get('articul', 'N/A')}")
        print(f"catalogId: {product.get('catalogId', 'N/A')}")
        print(f"Категория: {product.get('catalogHeader', 'N/A')}")
        
        # Информация о объекте catalog
        if 'catalog' in product and product['catalog']:
            print(f"\nОбъект catalog:")
            print(f"  id: {product['catalog'].get('id')}")
            print(f"  header: {product['catalog'].get('header')}")
            print(f"  parentId: {product['catalog'].get('parentId')}")
            print(f"  enabled: {product['catalog'].get('enabled')}")
        
        print(f"\nАктивен: {product.get('enabled', 'N/A')}")
        print(f"Удален: {product.get('deleted', 'N/A')}")
        print(f"Создан: {product.get('createdAt', 'N/A')}")
        print(f"Обновлен: {product.get('updatedAt', 'N/A')}")
        
        print(f"\n📄 Полный JSON товара:")
        print(json.dumps(product, ensure_ascii=False, indent=2))
    else:
        print(f"\n❌ Товар с ID={product_id} не найден!")


if __name__ == "__main__":
    main()

