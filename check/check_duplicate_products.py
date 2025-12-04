#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки товаров на дубликаты в PIM по articul (code_1c)
Сохраняет ID дубликатов для последующего удаления
"""

import os
import json
import asyncio
import aiohttp
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()



PIM_API_URL = os.getenv("PRODUCT_BASE")
PIM_LOGIN = os.getenv("LOGIN_TEST")
PIM_PASSWORD = os.getenv("PASSWORD_TEST")
CATALOG_1C_ID = 22


async def get_pim_token(session):
    """Получить токен авторизации PIM API"""
    auth_data = {"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
    async with session.post(f"{PIM_API_URL}/sign-in/", json=auth_data) as response:
        if response.status == 200:
            data = await response.json()
            if data.get("success") and data.get("data", {}).get("access", {}).get("token"):
                return data["data"]["access"]["token"]
    return None


async def fetch_all_products(session, token):
    """Загрузка всех товаров из каталога через scroll API"""
    headers = {"Authorization": f"Bearer {token}"}
    all_products = []
    scroll_id = None
    page = 0
    
    print("📥 Загрузка товаров из PIM...")
    
    while True:
        page += 1
        if scroll_id:
            url = f"{PIM_API_URL}/product/scroll/?scrollId={scroll_id}&catalogId={CATALOG_1C_ID}"
        else:
            url = f"{PIM_API_URL}/product/scroll?catalogId={CATALOG_1C_ID}"
        
        try:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    text = await response.text()
                    print(f"❌ Ошибка HTTP {response.status} на странице {page}: {text[:200]}")
                    break
                
                data = await response.json()
                if not data.get("success"):
                    print(f"❌ Ошибка в ответе API: {data.get('message', 'Unknown error')}")
                    break
                
                scroll_data = data.get("data", {})
                products = scroll_data.get("products", [])
                
                # Проверяем альтернативное поле
                if not products:
                    products = scroll_data.get("productElasticDtos", [])
                
                if not products:
                    break
                
                all_products.extend(products)
                print(f"📄 Страница {page}: загружено {len(products)} товаров (всего: {len(all_products)})")
                
                scroll_id = scroll_data.get("scrollId")
                if not scroll_id:
                    break
                    
        except Exception as e:
            print(f"❌ Ошибка на странице {page}: {e}")
            import traceback
            traceback.print_exc()
            break
    
    print(f"✅ Всего загружено {len(all_products)} товаров\n")
    return all_products


def find_duplicates(products):
    """Поиск дубликатов по articul (code_1c)"""
    print("🔍 Поиск дубликатов по articul (code_1c)...")
    
    # Группируем товары по articul (code_1c)
    articuls_map = defaultdict(list)
    
    for product in products:
        articul = product.get("articul")
        if articul:
            articul_str = str(articul).strip()
            if articul_str:
                articuls_map[articul_str].append({
                    "id": product.get("id"),
                    "articul": articul_str,
                    "header": product.get("header")
                })
    
    # Находим дубликаты (где больше 1 товара с одинаковым articul)
    duplicates = {}
    for articul, products_list in articuls_map.items():
        if len(products_list) > 1:
            # Сортируем по ID (первый созданный - оставляем, остальные - дубликаты)
            products_list.sort(key=lambda x: x["id"])
            duplicates[articul] = {
                "keep": products_list[0],
                "duplicates": products_list[1:]
            }
    
    print(f"✅ Найдено {len(duplicates)} code_1c с дубликатами\n")
    return duplicates


def save_duplicates(duplicates, output_file="duplicate_products.json"):
    """Сохранение дубликатов в JSON файл"""
    result = {
        "total_duplicate_articles": len(duplicates),
        "total_duplicate_products": sum(len(d["duplicates"]) for d in duplicates.values()),
        "duplicates": duplicates
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"💾 Результаты сохранены в {output_file}")
    return result


def save_ids_for_deletion(duplicates, output_file="duplicate_ids_for_deletion.json"):
    """Сохранение только ID дубликатов для удаления"""
    ids_to_delete = []
    details = []
    
    for articul, data in duplicates.items():
        for dup in data["duplicates"]:
            ids_to_delete.append(dup["id"])
            details.append({
                "id": dup["id"],
                "articul": articul,
                "header": dup.get("header"),
                "keep_id": data["keep"]["id"]
            })
    
    result = {
        "total_ids": len(ids_to_delete),
        "ids": ids_to_delete,
        "details": details
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"💾 ID для удаления сохранены в {output_file}")
    return result


async def main():
    try:
        async with aiohttp.ClientSession() as session:
            print("🔐 Авторизация в PIM API...")
            token = await get_pim_token(session)
            if not token:
                print("❌ Ошибка авторизации в PIM")
                return
            print("✅ Авторизация успешна\n")
            
            # Загружаем все товары
            products = await fetch_all_products(session, token)
            
            if not products:
                print("❌ Товары не загружены")
                return
            
            # Ищем дубликаты
            duplicates = find_duplicates(products)
            
            if not duplicates:
                print("✅ Дубликатов не найдено!")
                return
            
            # Сохраняем результаты
            save_duplicates(duplicates, "duplicate_products.json")
            save_ids_for_deletion(duplicates, "duplicate_ids_for_deletion.json")
            
            # Выводим статистику
            total_duplicates = sum(len(d["duplicates"]) for d in duplicates.values())
            print(f"\n📊 Статистика:")
            print(f"   - Code_1C с дубликатами: {len(duplicates)}")
            print(f"   - Всего дубликатов для удаления: {total_duplicates}")
            print(f"   - Товаров оставить: {len(duplicates)}")
            print(f"   - Товаров удалить: {total_duplicates}")
            
            # Показываем первые 10 примеров
            print(f"\n📋 Примеры дубликатов (первые 10):")
            for idx, (articul, data) in enumerate(list(duplicates.items())[:10], 1):
                print(f"\n   {idx}. Code_1C: {articul}")
                print(f"      Оставить: ID={data['keep']['id']}, header={data['keep'].get('header')[:50]}")
                for dup in data["duplicates"]:
                    print(f"      Удалить: ID={dup['id']}, header={dup.get('header')[:50]}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

