#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания новых товаров в PIM системе
Создает товары из таблицы products с is_new=true в каталоге 1С (id=22)
"""

import os
import requests
import asyncio
import aiohttp
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PIM_API_URL = os.getenv("PIM_API_URL")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")
CATALOG_1C_ID = 22  # Каталог "Уровень - 1с"


async def get_pim_token(session):
    """Получить токен авторизации PIM API"""
    auth_data = {"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
    async with session.post(f"{PIM_API_URL}/sign-in/", json=auth_data) as response:
        if response.status == 200:
            data = await response.json()
            if data.get("success") and data.get("data", {}).get("access", {}).get("token"):
                return data["data"]["access"]["token"]
    return None


def prepare_product_data(product):
    """Подготавливает данные товара для создания в PIM"""
    return {
        "header": product.get("product_name") or "",
        "headerAuto": None,
        "fullHeader": None,
        "barCode": product.get("barcode"),
        "articul": product.get("code_1c"),
        "content": None,
        "description": None,
        "price": 0.0,
        "enabled": True,
        "syncUid": product.get("uid"),
        "catalogId": CATALOG_1C_ID,
        "unit": None,
        "picture": None,
        "supplier": None,
        "manufacturer": None,
        "brand": None,
        "country": None,
        "manufacturerSeries": None,
        "productTags": [],
        "productSystemTags": [
            {"id": 4, "header": "Товар без шаблона", "syncUid": "null-template-product"},
            {"id": 1, "header": "Незаполненный товар", "syncUid": "unfilled-product"},
            {"id": 5, "header": "Товар без доп.категории", "syncUid": "product-without-additional-category"},
            {"id": 3, "header": "Товар без категории", "syncUid": "null-catalog-product"}
        ],
        "analogs": None,
        "relatedGoods": None,
        "featureValues": [],
        "catalogs": [],
        "terms": [],
        "videos": [],
        "pictures": [],
        "codes": [{"code": product.get("code_1c"), "codeType": "1C"}],
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
        "width": None,
        "height": None,
        "length": None,
        "weight": None,
        "volume": None,
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


async def create_product_in_pim(session, token, product, supabase_client):
    """Создает товар в PIM и обновляет id в Supabase"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    product_data = prepare_product_data(product)
    temp_id = product["id"]  # Временный отрицательный id
    
    try:
        async with session.post(
            f"{PIM_API_URL}/product/",
            json=product_data,
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("success") and data.get("data"):
                    pim_id = data["data"].get("id")
                    # Обновляем id в Supabase
                    supabase_client.table("products").update({
                        "id": pim_id,
                        "is_new": False
                    }).eq("id", temp_id).execute()
                    return pim_id
            text = await response.text()
            print(f"❌ Ошибка создания товара {product.get('code_1c')}: {response.status} - {text}")
            return None
    except Exception as e:
        print(f"❌ Ошибка при создании товара {product.get('code_1c')}: {e}")
        return None


async def main():
    try:
        # Подключение к Supabase
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Подключение к Supabase установлено")
        
        # Получаем новые товары (is_new=true и отрицательные id)
        print("📊 Загрузка новых товаров из базы...")
        response = supabase.table("products").select("*").eq("is_new", True).lt("id", 0).execute()
        new_products = response.data or []
        
        if not new_products:
            print("✅ Нет новых товаров для создания")
            return
        
        print(f"✅ Найдено {len(new_products)} новых товаров")
        
        # Авторизация в PIM
        async with aiohttp.ClientSession() as session:
            print("🔐 Авторизация в PIM API...")
            token = await get_pim_token(session)
            if not token:
                print("❌ Ошибка авторизации в PIM")
                return
            print("✅ Авторизация успешна")
            
            # Создаем товары
            total = len(new_products)
            success = 0
            failed = 0
            
            for idx, product in enumerate(new_products, 1):
                pim_id = await create_product_in_pim(session, token, product, supabase)
                if pim_id:
                    success += 1
                    print(f"📝 [{idx}/{total}] ✅ Создан товар {product.get('code_1c')} → PIM ID: {pim_id}")
                else:
                    failed += 1
                    print(f"📝 [{idx}/{total}] ❌ Ошибка создания товара {product.get('code_1c')}")
                
                if idx % 10 == 0:
                    print(f"📊 Прогресс: {success} успешно / {failed} ошибок / {idx} обработано")
            
            print(f"\n🎉 Завершено! Создано: {success}, Ошибок: {failed}, Всего: {total}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

