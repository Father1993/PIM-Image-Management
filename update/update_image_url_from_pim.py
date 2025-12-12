#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обновляет ссылки на картинки из PIM в поле image_url для товаров с is_new_product = true.
Использует прямые запросы к PIM API по ID товара.
"""

import asyncio
import os
from dotenv import load_dotenv
import aiohttp

load_dotenv()

# Supabase
SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = "products"
PAGE_SIZE = 1000
CONCURRENCY = int(os.getenv("IMAGE_URL_CONCURRENCY", "50"))

# PIM API
PIM_API_URL = os.getenv("PIM_API_URL")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")
PIM_IMAGE_BASE = "https://pim.uroven.pro/pictures/originals"

REST_URL = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}" if SUPABASE_URL else ""


def build_headers():
    return {
        "apikey": SUPABASE_KEY or "",
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }


async def get_pim_token(session):
    """Получить токен авторизации PIM API"""
    auth_data = {"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
    async with session.post(f"{PIM_API_URL}/sign-in/", json=auth_data) as response:
        if response.status == 200:
            data = await response.json()
            if data.get("success") and data.get("data", {}).get("access", {}).get("token"):
                return data["data"]["access"]["token"]
    return None


async def fetch_supabase_products(session):
    """Получить ID товаров с is_new_product = true из Supabase"""
    pim_ids = []
    offset = 0
    
    while True:
        params = {
            "select": "id",
            "is_new_product": "eq.true",
            "limit": PAGE_SIZE,
            "offset": offset
        }
        async with session.get(REST_URL, params=params, headers=build_headers()) as resp:
            if resp.status == 416 or resp.status != 200:
                break
            batch = await resp.json()
            if not batch:
                break
            pim_ids.extend([p["id"] for p in batch if p.get("id")])
            offset += PAGE_SIZE
            if len(batch) < PAGE_SIZE:
                break
    
    return pim_ids


async def get_product_image(session, token, pim_id, debug=False):
    """Получить URL картинки для конкретного товара из PIM"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        async with session.get(f"{PIM_API_URL}/product/{pim_id}", headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("success"):
                    product = data.get("data", {})
                    picture = product.get("picture")
                    
                    if debug:
                        print(f"\n🔍 DEBUG для товара {pim_id}:")
                        print(f"   picture: {picture}")
                    
                    # Проверяем наличие picture с полем name
                    if picture and isinstance(picture, dict) and picture.get("name"):
                        picture_name = picture["name"]
                        url = f"{PIM_IMAGE_BASE}/{picture_name}.JPG"
                        if debug:
                            print(f"   ✅ URL: {url}")
                        return url
                    elif debug:
                        print(f"   ❌ Нет картинки")
            elif debug:
                print(f"\n🔍 DEBUG для товара {pim_id}: HTTP {response.status}")
    except Exception as e:
        if debug:
            print(f"\n🔍 DEBUG для товара {pim_id}: Exception {e}")
    
    return None


async def update_product_image(session, semaphore, token, pim_id, stats, debug=False):
    """Получить картинку из PIM и обновить image_url в Supabase"""
    async with semaphore:
        # Получаем URL картинки из PIM
        image_url = await get_product_image(session, token, pim_id, debug=debug)
        
        if not image_url:
            stats['no_image'] += 1
            return False
        
        # Обновляем в Supabase
        params = {"id": f"eq.{pim_id}"}
        payload = {"image_url": image_url}
        
        try:
            async with session.patch(REST_URL, params=params, json=payload, headers=build_headers()) as resp:
                if resp.status in (200, 204):
                    stats['updated'] += 1
                    if debug:
                        print(f"   ✅ Обновлено в Supabase")
                    return True
                else:
                    stats['failed'] += 1
                    if debug:
                        print(f"   ❌ Ошибка обновления в Supabase: HTTP {resp.status}")
                    return False
        except Exception as e:
            stats['failed'] += 1
            if debug:
                print(f"   ❌ Exception при обновлении: {e}")
            return False


async def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Установите SUPABASE_URL и SUPABASE_KEY в .env")
        return
    
    if not PIM_LOGIN or not PIM_PASSWORD:
        print("❌ Установите LOGIN_TEST/PIM_LOGIN и PASSWORD_TEST/PIM_PASSWORD в .env")
        return
    
    timeout = aiohttp.ClientTimeout(total=None)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Авторизация в PIM
        print("🔐 Авторизация в PIM API...")
        token = await get_pim_token(session)
        if not token:
            print("❌ Ошибка авторизации в PIM")
            return
        print("✅ Авторизация успешна\n")
        
        # Получаем товары из Supabase
        print("📋 Получение товаров из Supabase...")
        pim_ids = await fetch_supabase_products(session)
        if not pim_ids:
            print("✅ Нет товаров с is_new_product = true")
            return
        print(f"✅ Найдено товаров: {len(pim_ids)}\n")
        
        # Обновляем image_url
        print(f"🚀 Обновление image_url (параллельно {CONCURRENCY})...")
        print(f"🔍 Включен DEBUG режим для первых 3 товаров\n")
        semaphore = asyncio.Semaphore(CONCURRENCY)
        
        # Статистика для отладки
        stats = {'updated': 0, 'no_image': 0, 'failed': 0}
        
        # Создаем задачи с DEBUG для первых 3 товаров
        tasks = []
        for idx, pid in enumerate(pim_ids):
            debug = idx < 3  # DEBUG только для первых 3
            tasks.append(update_product_image(session, semaphore, token, pid, stats, debug=debug))
        
        for idx, coro in enumerate(asyncio.as_completed(tasks), 1):
            await coro
            
            if idx % 100 == 0 or idx == len(pim_ids):
                percent = (idx / len(pim_ids) * 100) if pim_ids else 0
                print(f"⏳ Обработано: {idx}/{len(pim_ids)} ({percent:.1f}%) | "
                      f"Обновлено: {stats['updated']} | "
                      f"Без картинки: {stats['no_image']} | "
                      f"Ошибок: {stats['failed']}")
        
        print(f"\n✅ Готово. Обновлено товаров: {stats['updated']}/{len(pim_ids)}")
        print(f"📊 Статистика:")
        print(f"   - Обновлено: {stats['updated']}")
        print(f"   - Без картинки в PIM: {stats['no_image']}")
        print(f"   - Ошибок обновления: {stats['failed']}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"❌ Ошибка: {exc}")
        import traceback
        traceback.print_exc()
