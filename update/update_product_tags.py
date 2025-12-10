#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обновляет теги товаров в каталоге 21, добавляя все теги кроме id=10.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

load_dotenv()

PIM_API_URL = (os.getenv("PIM_API_URL") or "").rstrip("/")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")
CATALOG_ID = 21
CONCURRENT = int(os.getenv("MATRIX_CONCURRENT", "50"))
DRY_RUN = os.getenv("MATRIX_DRY_RUN", "").lower() == "true"
TAGS_FILE = Path(__file__).resolve().parents[1] / "data" / "tags_pim.json"


def require_settings():
    missing = [
        name
        for name, value in (
            ("PIM_API_URL", PIM_API_URL),
            ("PIM_LOGIN", PIM_LOGIN),
            ("PIM_PASSWORD", PIM_PASSWORD),
        )
        if not value
    ]
    if missing:
        raise SystemExit(f"❌ Отсутствуют переменные окружения: {', '.join(missing)}")


def load_tags():
    """Загрузить теги, исключая тег с id=10"""
    with open(TAGS_FILE, "r", encoding="utf-8") as f:
        all_tags = json.load(f)
    return [tag for tag in all_tags if tag.get("id") != 10]


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


async def fetch_products(session, token):
    """Получить все товары из каталога через scroll API"""
    headers = {"Authorization": f"Bearer {token}"}
    products = []
    scroll_id = None
    
    while True:
        url = f"{PIM_API_URL}/product/scroll"
        params = {"catalogId": CATALOG_ID}
        if scroll_id:
            params["scrollId"] = scroll_id
        
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status == 403:
                token = await get_pim_token(session)
                headers["Authorization"] = f"Bearer {token}"
                continue
            if resp.status != 200:
                break
            
            data = await resp.json()
            scroll_data = data.get("data", {})
            batch = scroll_data.get("products") or scroll_data.get("productElasticDtos") or []
            
            if not batch:
                break
            
            products.extend(batch)
            print(f"📥 Загружено товаров: {len(products)}")
            
            scroll_id = scroll_data.get("scrollId")
            if not scroll_id:
                break
    
    return products, token


async def fetch_product(session, token, product_id):
    """Загрузить полные данные товара"""
    headers = {"Authorization": f"Bearer {token}"}
    async with session.get(f"{PIM_API_URL}/product/{product_id}", headers=headers) as resp:
        if resp.status == 403:
            token = await get_pim_token(session)
            headers["Authorization"] = f"Bearer {token}"
            async with session.get(f"{PIM_API_URL}/product/{product_id}", headers=headers) as resp2:
                if resp2.status != 200:
                    return None
                data = await resp2.json()
                return data.get("data"), token
        if resp.status != 200:
            return None
        data = await resp.json()
        return data.get("data"), token


async def update_product(session, token, product_id, payload):
    """Обновить товар в PIM"""
    headers = {"Authorization": f"Bearer {token}"}
    async with session.post(f"{PIM_API_URL}/product/{product_id}", headers=headers, json=payload) as resp:
        if resp.status == 403:
            token = await get_pim_token(session)
            headers["Authorization"] = f"Bearer {token}"
            async with session.post(f"{PIM_API_URL}/product/{product_id}", headers=headers, json=payload) as resp2:
                if resp2.status != 200:
                    return False, token
                data = await resp2.json()
                return data.get("success", False), token
        if resp.status != 200:
            return False, token
        data = await resp.json()
        return data.get("success", False), token


async def process_product(session, token_ref, semaphore, product_id, tags):
    """Обработать один товар"""
    async with semaphore:
        token = token_ref[0]
        try:
            fetch_result = await fetch_product(session, token, product_id)
            if not fetch_result:
                return {"id": product_id, "status": "error"}
            
            product_data, token = fetch_result
            token_ref[0] = token
            
            if not product_data:
                return {"id": product_id, "status": "error"}
            
            # Объединяем существующие теги с новыми
            current_tags = product_data.get("productTags", [])
            current_tag_ids = {tag.get("id") for tag in current_tags if isinstance(tag, dict)}
            needed_tag_ids = {tag["id"] for tag in tags}
            
            if needed_tag_ids.issubset(current_tag_ids):
                return {"id": product_id, "status": "already_ok"}
            
            # Объединяем теги: существующие + новые (без дубликатов)
            merged_tags = list(current_tags)
            for tag in tags:
                if tag["id"] not in current_tag_ids:
                    merged_tags.append(tag)
            
            product_data["productTags"] = merged_tags
            
            if DRY_RUN:
                return {"id": product_id, "status": "updated"}
            
            success, token = await update_product(session, token, product_id, product_data)
            token_ref[0] = token
            
            return {"id": product_id, "status": "updated" if success else "error"}
        except Exception as e:
            return {"id": product_id, "status": "error", "error": str(e)}


async def main():
    require_settings()
    tags = load_tags()
    print(f"📋 Загружено тегов: {len(tags)} (исключен id=10)")
    
    async with aiohttp.ClientSession() as session:
        token = await get_pim_token(session)
        print("📥 Загрузка товаров из каталога 21...")
        products, token = await fetch_products(session, token)
        print(f"✅ Найдено товаров: {len(products)}")
        
        if not products:
            print("✅ Нет товаров для обновления")
            return
        
        token_ref = [token]
        semaphore = asyncio.Semaphore(CONCURRENT)
        stats = {"updated": 0, "already_ok": 0, "errors": 0}
        
        print(f"🔄 Обработка {len(products)} товаров (параллельно {CONCURRENT})...")
        tasks = [
            process_product(session, token_ref, semaphore, p["id"], tags)
            for p in products
        ]
        
        for idx, task in enumerate(asyncio.as_completed(tasks), 1):
            result = await task
            if result:
                status = result.get("status")
                if status == "updated":
                    stats["updated"] += 1
                elif status == "already_ok":
                    stats["already_ok"] += 1
                else:
                    stats["errors"] += 1
                
                if idx % 100 == 0:
                    print(f"✅ Обработано: {idx}/{len(products)} | Обновлено: {stats['updated']} | Ошибок: {stats['errors']}")
        
        print(f"\n✅ Готово. Обновлено: {stats['updated']}, уже правильные: {stats['already_ok']}, ошибок: {stats['errors']}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"❌ Критическая ошибка: {exc}")
        sys.exit(1)

