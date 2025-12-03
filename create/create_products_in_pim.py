#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания новых товаров в PIM системе
Создает товары из таблицы new_onec_products с правильными категориями
"""

import os
import asyncio
import aiohttp
import time
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PIM_API_URL = os.getenv("PRODUCT_BASE")
PIM_LOGIN = os.getenv("LOGIN_TEST")
PIM_PASSWORD = os.getenv("PASSWORD_TEST")
CATALOG_1C_ID = 22
TEST_LIMIT = 19110  # Тестовый запуск на 5 товаров


def normalize_name(name):
    """Нормализация названия категории"""
    if not name:
        return ""
    return " ".join(name.strip().split())


async def get_pim_token(session):
    """Получить токен авторизации PIM API"""
    auth_data = {"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
    async with session.post(f"{PIM_API_URL}/sign-in/", json=auth_data) as response:
        if response.status == 200:
            data = await response.json()
            if data.get("success") and data.get("data", {}).get("access", {}).get("token"):
                return data["data"]["access"]["token"]
    return None


async def load_categories(session, token):
    """Загрузка всех категорий из PIM"""
    headers = {"Authorization": f"Bearer {token}"}
    async with session.get(f"{PIM_API_URL}/catalog/{CATALOG_1C_ID}", headers=headers) as response:
        if response.status != 200:
            return {}, None
        
        data = await response.json()
        catalog_data = data.get("data", {})
        categories_by_path = {}
        root_category = None
        
        def parse_tree(cat, parent_path=""):
            name = normalize_name(cat.get("header", ""))
            if parent_path:
                full_path = f"{parent_path} / {name}"
            else:
                full_path = name
            
            categories_by_path[full_path] = {
                "id": cat["id"],
                "header": cat["header"],
                "parentId": cat.get("parentId"),
                "full_path": full_path
            }
            
            if cat["id"] == CATALOG_1C_ID:
                nonlocal root_category
                root_category = categories_by_path[full_path]
            
            for child in cat.get("children", []):
                parse_tree(child, full_path)
        
        parse_tree(catalog_data)
        return categories_by_path, root_category


async def create_category(session, token, header, parent_id):
    """Создание категории в PIM"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {
        "id": 0,
        "parentId": parent_id,
        "header": header,
        "enabled": True,
        "deleted": False,
        "lastLevel": True,
        "pos": 500
    }
    
    async with session.post(f"{PIM_API_URL}/catalog/rapid", headers=headers, json=data) as response:
        if response.status == 200:
            result = await response.json()
            return result.get("success", False)
    return False


async def ensure_category_path(session, token, groups, categories_by_path, root_category):
    """Создает цепочку категорий из group1-group10"""
    if not groups or not any(groups):
        return None
    
    current_parent_id = root_category["id"]
    current_path = normalize_name(root_category["header"])
    
    for group_name in groups:
        if not group_name or not group_name.strip():
            continue
        
        normalized = normalize_name(group_name)
        next_path = f"{current_path} / {normalized}"
        
        if next_path in categories_by_path:
            current_parent_id = categories_by_path[next_path]["id"]
            current_path = next_path
        else:
            if await create_category(session, token, group_name, current_parent_id):
                await asyncio.sleep(1)
                new_categories, _ = await load_categories(session, token)
                categories_by_path.update(new_categories)
                if next_path in categories_by_path:
                    current_parent_id = categories_by_path[next_path]["id"]
                    current_path = next_path
                else:
                    return None
            else:
                return None
    
    return categories_by_path.get(current_path)


def prepare_product_data(product, category_obj, root_category):
    """Подготовка данных товара для создания в PIM"""
    catalog_obj = category_obj if category_obj else root_category
    
    def safe_float(value):
        try:
            return float(value) if value else None
        except (ValueError, TypeError):
            return None
    
    return {
        "header": product.get("product_name") or "",
        "headerAuto": None,
        "fullHeader": None,
        "barCode": product.get("barcode"),
        "articul": product.get("code_1c") or product.get("article"),
        "content": None,
        "description": None,
        "price": 0.0,
        "enabled": True,
        "syncUid": product.get("uid"),
        "catalog": {
            "id": catalog_obj["id"],
            "header": catalog_obj["header"],
            "parentId": catalog_obj.get("parentId", CATALOG_1C_ID),
            "enabled": True
        },
        "catalogId": catalog_obj["id"],
        "weight": safe_float(product.get("weight")),
        "volume": safe_float(product.get("volume")),
        "length": safe_float(product.get("length")),
        "width": None,
        "height": None,
        "unit": None,
        "picture": None,
        "supplier": None,
        "manufacturer": None,
        "brand": None,
        "country": None,
        "manufacturerSeries": None,
        "productTags": [],
        "productSystemTags": [],
        "analogs": None,
        "relatedGoods": None,
        "featureValues": [],
        "catalogs": [],
        "terms": [],
        "videos": [],
        "pictures": [],
        "codes": [{"code": product.get("code_1c") or product.get("article"), "codeType": "1C"}] if product.get("code_1c") or product.get("article") else [],
        "codeDataJson": None,
        "prices": [],
        "remains": [],
        "documents": [],
        "documentLinks": [],
        "packing": [],
        "pos": 500,
        "supplyTerm": None,
        "parentId": None,
        "productClassId": None,
        "parent": None,
        "linkedGoods": [],
        "productStatus": None,
        "productGroup": None,
        "featureUnionCondition": None,
        "productStatusId": None,
        "supplierId": None,
        "manufacturerId": None,
        "brandId": None,
        "countryId": None,
        "manufacturerSeriesId": None,
        "featureUnionConditionId": None,
        "productGroupId": None,
        "unitId": None,
        "pictureId": None,
        "guaranty": None,
        "deleted": False,
        "pictureInput": None,
        "deletePicture": False,
        "commercePrice": None,
        "balancesOnGroupsOfWarehouses": None,
        "manufacturerSiteLink": None,
        "multiplicitySupplier": None,
        "multiplicityOrder": None,
        "minOrderQuantity": None,
        "productNextArrival": None,
        "tax": None,
        "taxId": None,
        "htHead": None,
        "htDesc": None,
        "htKeywords": None,
        "url": None
    }


async def check_product_exists(session, token, code_1c):
    """Проверка существования товара по code_1c через scroll API"""
    if not code_1c:
        return None
    
    code_1c_str = str(code_1c).strip()
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Используем scroll API для поиска по каталогу
        url = f"{PIM_API_URL}/product/scroll"
        params = {"catalogId": CATALOG_1C_ID}
        scroll_id = None
        max_pages = 50  # Увеличиваем лимит для более тщательного поиска
        
        for page in range(max_pages):
            if scroll_id:
                url = f"{PIM_API_URL}/product/scroll"
                params = {"scrollId": scroll_id, "catalogId": CATALOG_1C_ID}
            
            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    break
                
                data = await response.json()
                if not data.get("success"):
                    break
                
                scroll_data = data.get("data", {})
                products = scroll_data.get("products", [])
                
                # Проверяем товары в текущей порции
                for p in products:
                    # Проверяем articul (это code_1c в PIM)
                    if str(p.get("articul", "")).strip() == code_1c_str:
                        return p.get("id")
                    
                    # Проверяем массив codes (там тоже может быть код 1С)
                    codes = p.get("codes", {})
                    if isinstance(codes, dict):
                        # Проверяем различные типы кодов
                        for code_type, code_value in codes.items():
                            if code_value and str(code_value).strip() == code_1c_str:
                                return p.get("id")
                    elif isinstance(codes, list):
                        # Если codes - массив объектов
                        for code_obj in codes:
                            if isinstance(code_obj, dict):
                                code_value = code_obj.get("code") or code_obj.get("value")
                                code_type = code_obj.get("codeType", "")
                                # Проверяем код типа "1C"
                                if code_type == "1C" and code_value and str(code_value).strip() == code_1c_str:
                                    return p.get("id")
                
                # Получаем scroll_id для следующей порции
                scroll_id = scroll_data.get("scrollId")
                if not scroll_id or not products:
                    break
        
        return None
    except Exception:
        return None


async def create_product_in_pim(session, token_ref, product, category_obj, root_category):
    """Создает товар в PIM с автоматическим обновлением токена при 403"""
    code_1c = product.get("code_1c")
    
    # Проверяем существование товара по code_1c перед созданием
    if code_1c:
        existing_id = await check_product_exists(session, token_ref[0], code_1c)
        if existing_id:
            return existing_id
    
    product_data = prepare_product_data(product, category_obj, root_category)
    token = token_ref[0]
    
    async def make_request(token):
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        async with session.post(f"{PIM_API_URL}/product/", json=product_data, headers=headers) as response:
            status = response.status
            if status == 200:
                data = await response.json()
                if data.get("success"):
                    result_data = data.get("data")
                    if isinstance(result_data, str):
                        try:
                            return int(result_data), None
                        except (ValueError, TypeError):
                            pass
                    elif isinstance(result_data, dict):
                        return result_data.get("id"), None
            text = await response.text()
            return None, (status, text)
    
    pim_id, error = await make_request(token)
    if pim_id:
        return pim_id
    
    # Если 403, обновляем токен и повторяем
    if error and error[0] == 403:
        print(f"⚠️  Токен истек, обновляем...")
        new_token = await get_pim_token(session)
        if new_token:
            token_ref[0] = new_token
            pim_id, error = await make_request(new_token)
            if pim_id:
                return pim_id
    
    if error:
        print(f"❌ Ошибка создания товара {articul}: {error[0]} - {error[1][:200]}")
    return None


async def main():
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Подключение к Supabase установлено")
        
        print(f"📊 Загрузка товаров из new_onec_products (лимит: {TEST_LIMIT})...")
        response = supabase.table("new_onec_products").select("*").limit(TEST_LIMIT).execute()
        products = response.data or []
        
        if not products:
            print("✅ Нет товаров для создания")
            return
        
        print(f"✅ Найдено {len(products)} товаров")
        
        async with aiohttp.ClientSession() as session:
            print("🔐 Авторизация в PIM API...")
            token = await get_pim_token(session)
            if not token:
                print("❌ Ошибка авторизации в PIM")
                return
            print("✅ Авторизация успешна")
            
            print("📂 Загрузка категорий из PIM...")
            categories_by_path, root_category = await load_categories(session, token)
            print(f"✅ Загружено {len(categories_by_path)} категорий")
            
            success = 0
            failed = 0
            skipped = 0
            token_ref = [token]  # Список для передачи по ссылке
            token_time = time.time()
            checked_articuls = {}  # Кэш проверенных артикулов
            
            for idx, product in enumerate(products, 1):
                # Обновляем токен каждые 50 минут (3000 секунд)
                if time.time() - token_time > 3000:
                    print("🔄 Профилактическое обновление токена...")
                    new_token = await get_pim_token(session)
                    if new_token:
                        token_ref[0] = new_token
                        token_time = time.time()
                        print("✅ Токен обновлен")
                
                groups = [
                    product.get("group1"),
                    product.get("group2"),
                    product.get("group3"),
                    product.get("group4"),
                    product.get("group5"),
                    product.get("group6"),
                    product.get("group7"),
                    product.get("group8"),
                    product.get("group9"),
                    product.get("group10")
                ]
                
                category_obj = await ensure_category_path(session, token_ref[0], groups, categories_by_path, root_category)
                if not category_obj:
                    category_obj = root_category
                
                code_1c = product.get('code_1c')
                articul = code_1c or product.get('article')
                
                # Проверяем кэш перед созданием (только по code_1c)
                if code_1c and code_1c in checked_articuls:
                    existing_id = checked_articuls[code_1c]
                    if existing_id:
                        skipped += 1
                        print(f"📝 [{idx}/{len(products)}] ⏭️  Товар {code_1c} уже существует → PIM ID: {existing_id}")
                        continue
                
                pim_id = await create_product_in_pim(session, token_ref, product, category_obj, root_category)
                
                if pim_id:
                    success += 1
                    if code_1c:
                        checked_articuls[code_1c] = pim_id  # Сохраняем в кэш по code_1c
                    print(f"📝 [{idx}/{len(products)}] ✅ Товар {code_1c} → PIM ID: {pim_id}")
                else:
                    failed += 1
                    if code_1c:
                        checked_articuls[code_1c] = None  # Помечаем как неудачный
                    print(f"📝 [{idx}/{len(products)}] ❌ Ошибка создания товара {code_1c}")
            
            print(f"\n🎉 Завершено! Создано: {success}, Пропущено: {skipped}, Ошибок: {failed}, Всего: {len(products)}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

