#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки созданных товаров в PIM
Проверяет корректность создания, категории и обновления в Supabase
"""

import os
import sys
import requests
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Конфигурация
PIM_API_URL = os.getenv("PRODUCT_BASE")
PIM_LOGIN = os.getenv("LOGIN_TEST")
PIM_PASSWORD = os.getenv("PASSWORD_TEST")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def authenticate():
    """Авторизация в PIM API"""
    response = requests.post(
        f"{PIM_API_URL}/sign-in/",
        json={"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
    )
    response.raise_for_status()
    return response.json()["data"]["access"]["token"]


def get_product_from_pim(token, pim_id):
    """Получение товара из PIM по ID"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(
            f"{PIM_API_URL}/product/{pim_id}",
            headers=headers,
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("data"):
                return data["data"]
        return None
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Ошибка запроса: {e}")
        return None


def check_products_by_ids(pim_ids):
    """Проверка товаров по списку PIM ID"""
    print("🔐 Авторизация в PIM API...")
    token = authenticate()
    print("✅ Авторизация успешна\n")
    
    print(f"📦 Проверка {len(pim_ids)} товаров в PIM...\n")
    
    for idx, pim_id in enumerate(pim_ids, 1):
        print(f"[{idx}/{len(pim_ids)}] Проверка товара ID={pim_id}...")
        product = get_product_from_pim(token, pim_id)
        
        if not product:
            print(f"   ❌ Товар не найден в PIM")
            continue
        
        print(f"   ✅ Название: {product.get('header', 'N/A')}")
        print(f"   🔢 Артикул: {product.get('articul', 'N/A')}")
        print(f"   📂 Категория: {product.get('catalog', {}).get('header', 'N/A')} (ID: {product.get('catalogId', 'N/A')})")
        print(f"   🔗 Ссылка: {PIM_API_URL.replace('/api/v1', '')}/product/{pim_id}")
        print(f"   ✅ Активен: {'Да' if product.get('enabled') else 'Нет'}")
        print()


def check_products_from_supabase(limit=None):
    """Проверка товаров из Supabase, которые были созданы недавно"""
    print("📦 Подключение к Supabase...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Подключение установлено\n")
    
    # Получаем товары, которые были созданы в PIM (есть link_pim и is_new=false)
    print("📋 Получение товаров из Supabase (push_to_pim=true)...")
    query = client.table("products").select("*").eq("push_to_pim", True).order("updated_at", desc=True)
    if limit:
        query = query.limit(limit)
    response = query.execute()
    products = response.data
    print(f"✅ Найдено {len(products)} товаров\n")
    
    if not products:
        print("❌ Нет товаров для проверки")
        return
    
    # Извлекаем PIM ID из link_pim
    pim_ids = []
    for product in products:
        link_pim = product.get("link_pim", "")
        if link_pim:
            # Извлекаем ID из ссылки вида: https://.../product/28200
            try:
                pim_id = int(link_pim.split("/")[-1])
                pim_ids.append((pim_id, product))
            except (ValueError, IndexError):
                print(f"⚠️  Не удалось извлечь ID из ссылки: {link_pim}")
    
    if not pim_ids:
        print("❌ Не найдено валидных PIM ID")
        return
    
    print(f"🔍 Проверка {len(pim_ids)} товаров...\n")
    
    # Авторизация в PIM
    print("🔐 Авторизация в PIM API...")
    token = authenticate()
    print("✅ Авторизация успешна\n")
    
    # Проверяем каждый товар
    success_count = 0
    error_count = 0
    
    for idx, (pim_id, supabase_product) in enumerate(pim_ids, 1):
        product_name = supabase_product.get("product_name", "Без имени")
        code_1c = supabase_product.get("code_1c", "N/A")
        
        print(f"[{idx}/{len(pim_ids)}] {product_name[:50]}...")
        print(f"   🔢 Код 1С: {code_1c}")
        print(f"   📋 Supabase ID: {supabase_product.get('id')}")
        print(f"   🔗 Link PIM: {supabase_product.get('link_pim', 'N/A')}")
        print(f"   ✅ is_new: {supabase_product.get('is_new', 'N/A')}")
        print(f"   ✅ push_to_pim: {supabase_product.get('push_to_pim', 'N/A')}")
        
        # Получаем товар из PIM
        pim_product = get_product_from_pim(token, pim_id)
        
        if not pim_product:
            print(f"   ❌ Товар не найден в PIM")
            error_count += 1
            print()
            continue
        
        # Проверяем соответствие данных
        print(f"   ✅ PIM Название: {pim_product.get('header', 'N/A')}")
        print(f"   ✅ PIM Артикул: {pim_product.get('articul', 'N/A')}")
        
        # Проверка категории
        catalog = pim_product.get("catalog", {})
        catalog_id = pim_product.get("catalogId")
        catalog_name = catalog.get("header", "N/A") if catalog else "N/A"
        print(f"   📂 PIM Категория: {catalog_name} (ID: {catalog_id})")
        
        # Проверка артикула
        pim_articul = pim_product.get("articul", "")
        if pim_articul != code_1c:
            print(f"   ⚠️  Артикул не совпадает! Supabase: {code_1c}, PIM: {pim_articul}")
        
        success_count += 1
        print()
    
    print(f"\n🎉 Проверка завершена!")
    print(f"   ✅ Успешно проверено: {success_count}")
    print(f"   ❌ Ошибок: {error_count}")


def main():
    # Проверка переменных окружения
    required_vars = ["PRODUCT_BASE", "LOGIN_TEST", "PASSWORD_TEST", "SUPABASE_URL", "SUPABASE_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"❌ Отсутствуют переменные окружения: {', '.join(missing)}")
        print("   Проверьте файл .env")
        return
    
    # Если переданы ID товаров как аргументы
    if len(sys.argv) > 1:
        try:
            pim_ids = [int(arg) for arg in sys.argv[1:]]
            check_products_by_ids(pim_ids)
        except ValueError:
            print("❌ Неверный формат ID. Используйте: python check_created_products.py 28200 28201 28202")
    else:
        # Проверяем последние созданные товары из Supabase
        limit = 10  # По умолчанию проверяем 10 последних
        check_products_from_supabase(limit)


if __name__ == "__main__":
    main()

