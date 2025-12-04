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
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PIM_API_URL = os.getenv("PIM_API_URL")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")
CATALOG_1C_ID = 22
TEST_LIMIT = 19100  # Тестовый запуск на 5 товаров


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


async def create_category(session, token, header, parent_id, is_last_level=False):
    """Создание категории в PIM"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {
        "id": 0,
        "parentId": parent_id,
        "header": header,
        "enabled": True,
        "deleted": False,
        "lastLevel": is_last_level,
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
    
    # Фильтруем пустые группы и находим последний непустой индекс
    non_empty_groups = [(idx, name) for idx, name in enumerate(groups) if name and name.strip()]
    if not non_empty_groups:
        return None
    
    current_parent_id = root_category["id"]
    current_path = normalize_name(root_category["header"])
    last_idx = non_empty_groups[-1][0]  # Индекс последнего непустого элемента
    
    for idx, group_name in non_empty_groups:
        normalized = normalize_name(group_name)
        next_path = f"{current_path} / {normalized}"
        is_last = (idx == last_idx)  # Это последний уровень?
        
        if next_path in categories_by_path:
            current_parent_id = categories_by_path[next_path]["id"]
            current_path = next_path
        else:
            if await create_category(session, token, group_name, current_parent_id, is_last_level=is_last):
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


async def create_product_in_pim(session, token_ref, product, category_obj, root_category):
    """Создает товар в PIM с автоматическим обновлением токена при 403"""
    code_1c = product.get("code_1c")
    code_1c_str = str(code_1c).strip() if code_1c else None
    display_code = code_1c_str or product.get('article') or 'N/A'
    
    product_data = prepare_product_data(product, category_obj, root_category)
    token = token_ref[0]
    
    async def make_request(token):
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        async with session.post(f"{PIM_API_URL}/product/rapid/", json=product_data, headers=headers) as response:
            status = response.status
            text = await response.text()
            
            if status == 200:
                try:
                    data = await response.json() if text else {}
                    if data.get("success"):
                        result_data = data.get("data")
                        if isinstance(result_data, str):
                            try:
                                return int(result_data), None
                            except (ValueError, TypeError):
                                pass
                        elif isinstance(result_data, dict):
                            return result_data.get("id"), None
                except Exception as e:
                    return None, (status, f"Ошибка парсинга ответа: {e}, текст: {text[:500]}")
            
            # Детальное логирование ошибки
            try:
                error_data = await response.json() if text else {}
                error_message = error_data.get("message", "") or error_data.get("errors", "") or text[:500]
            except:
                error_message = text[:500] if text else "Пустой ответ"
            
            return None, (status, error_message)
    
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
        print(f"❌ Ошибка создания товара {display_code}:")
        print(f"   Статус: {error[0]}")
        print(f"   Сообщение: {error[1]}")
        print(f"   Товар: {product.get('product_name', 'N/A')}")
        print(f"   Категория ID: {product_data.get('catalogId', 'N/A')}")
        print(f"   URL: {PIM_API_URL}/product/")
        print(f"   Данные запроса (JSON):")
        try:
            print(json.dumps(product_data, ensure_ascii=False, indent=2)[:1000])
        except:
            print("   [Не удалось сериализовать данные]")
    return None


async def main():
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Подключение к Supabase установлено")
        
        print(f"📊 Загрузка товаров из new_onec_products (push_to_pim=false, лимит: {TEST_LIMIT})...")
        response = supabase.table("new_onec_products").select("*").eq("push_to_pim", False).limit(TEST_LIMIT).execute()
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
            print(f"✅ Загружено {len(categories_by_path)} категорий\n")
            
            success = 0
            failed = 0
            token_ref = [token]  # Список для передачи по ссылке
            token_time = time.time()
            start_time = time.time()
            
            for idx, product in enumerate(products, 1):
                # Обновляем токен каждые 50 минут (3000 секунд) - токен живет 1 час
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
                display_code = str(code_1c).strip() if code_1c else product.get('article') or 'N/A'
                
                pim_id = await create_product_in_pim(session, token_ref, product, category_obj, root_category)
                
                if pim_id:
                    success += 1
                    # Обновляем флаг push_to_pim в Supabase
                    try:
                        supabase.table("new_onec_products").update({"push_to_pim": True}).eq("id", product.get("id")).execute()
                    except Exception as e:
                        print(f"⚠️  Ошибка обновления флага для товара {display_code}: {e}")
                    
                    print(f"📝 [{idx}/{len(products)}] ✅ Товар {display_code} → PIM ID: {pim_id}")
                else:
                    failed += 1
                    print(f"📝 [{idx}/{len(products)}] ❌ Ошибка создания товара {display_code}")
                
                # Выводим прогресс каждые 10 товаров
                if idx % 10 == 0:
                    elapsed = time.time() - start_time
                    speed = idx / elapsed if elapsed > 0 else 0
                    remaining = (len(products) - idx) / speed if speed > 0 else 0
                    print(f"📊 Прогресс: {idx}/{len(products)} | ✅ {success} | ❌ {failed} | Скорость: {speed:.1f} тов/сек | Осталось: ~{remaining/60:.1f} мин")
            
            elapsed_total = time.time() - start_time
            print(f"\n🎉 Завершено! Создано: {success}, Ошибок: {failed}, Всего: {len(products)}")
            print(f"⏱️  Время выполнения: {elapsed_total/60:.1f} минут")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

