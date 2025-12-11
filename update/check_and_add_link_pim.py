#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверяет и добавляет недостающие ссылки на PIM для товаров.
"""

import asyncio
import os
from dotenv import load_dotenv
import aiohttp

load_dotenv()

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = "products"
PIM_BASE_URL = "https://pim.uroven.pro/cabinet/pim/catalog/item/edit"
CONCURRENCY = int(os.getenv("LINK_PIM_CONCURRENCY", "50"))
PAGE_SIZE = 1000

REST_URL = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}" if SUPABASE_URL else ""


def build_headers():
    return {
        "apikey": SUPABASE_KEY or "",
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }


async def fetch_products_without_link(session):
    """Получить ID товаров без ссылок (NULL или пустая строка)"""
    ids = []
    offset = 0
    
    while True:
        url = f"{REST_URL}?select=id&or=(link_pim.is.null,link_pim.eq.)&limit={PAGE_SIZE}&offset={offset}"
        async with session.get(url, headers=build_headers()) as resp:
            if resp.status == 416:
                break
            if resp.status != 200:
                break
            batch = await resp.json()
            if not batch:
                break
            ids.extend([p["id"] for p in batch])
            offset += PAGE_SIZE
            if len(batch) < PAGE_SIZE:
                break
    
    return ids


async def update_product(session, semaphore, product_id):
    """Обновить ссылку для одного товара"""
    async with semaphore:
        link_pim = f"{PIM_BASE_URL}/{product_id}"
        params = {"id": f"eq.{product_id}"}
        payload = {"link_pim": link_pim}
        
        try:
            async with session.patch(REST_URL, params=params, json=payload, headers=build_headers()) as resp:
                return resp.status in (200, 204)
        except Exception:
            return False


async def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Установите SUPABASE_URL и SUPABASE_KEY в .env")
        return
    
    timeout = aiohttp.ClientTimeout(total=None)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        print("🔍 Проверка товаров без ссылок...")
        product_ids = await fetch_products_without_link(session)
        
        if not product_ids:
            print("✅ Все товары имеют ссылки на PIM")
            return
        
        print(f"📊 Найдено товаров без ссылок: {len(product_ids)}\n")
        
        print(f"🚀 Добавление ссылок (параллельно {CONCURRENCY})...")
        semaphore = asyncio.Semaphore(CONCURRENCY)
        tasks = [update_product(session, semaphore, pid) for pid in product_ids]
        
        updated = 0
        for idx, coro in enumerate(asyncio.as_completed(tasks), 1):
            if await coro:
                updated += 1
            
            if idx % 100 == 0 or idx == len(product_ids):
                percent = (idx / len(product_ids) * 100) if product_ids else 0
                print(f"⏳ Обработано: {idx}/{len(product_ids)} ({percent:.1f}%) | Обновлено: {updated}")
        
        print(f"\n✅ Готово. Обновлено товаров: {updated}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"❌ Ошибка: {exc}")
        import traceback
        traceback.print_exc()

