#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт подставляет pim_product_id в Supabase, находя товары в PIM по code_1c.
"""

import os
import time
from collections import defaultdict

import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = os.getenv("SUPABASE_MATRIX_TABLE", "new_onec_products")
PIM_API_URL = (os.getenv("PIM_API_URL") or "").rstrip("/")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")
CATALOG_ID = int(os.getenv("PIM_CATALOG_ID", "22"))
BATCH_SIZE = int(os.getenv("PIM_ID_RANGE_SIZE", "500"))
UPDATE_PAUSE = float(os.getenv("PIM_ID_UPDATE_PAUSE", "0"))
UPSERT_SIZE = int(os.getenv("PIM_ID_UPSERT_SIZE", "500"))


def ensure_settings():
    missing = [
        name
        for name, value in (
            ("SUPABASE_URL", SUPABASE_URL),
            ("SUPABASE_KEY", SUPABASE_KEY),
            ("PIM_API_URL", PIM_API_URL),
            ("PIM_LOGIN", PIM_LOGIN),
            ("PIM_PASSWORD", PIM_PASSWORD),
        )
        if not value
    ]
    if missing:
        raise SystemExit(f"❌ Нет переменных окружения: {', '.join(missing)}")


def normalize_code(value):
    if not value:
        return None
    return str(value).strip()


def get_token():
    payload = {"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
    response = requests.post(f"{PIM_API_URL}/sign-in/", json=payload, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"Ошибка авторизации: {response.status_code} {response.text[:200]}")
    token = response.json().get("data", {}).get("access", {}).get("token")
    if not token:
        raise RuntimeError("Не удалось получить токен PIM")
    return token


def fetch_pim_codes(token):
    headers = {"Authorization": f"Bearer {token}"}
    code_map = {}
    duplicates = defaultdict(list)
    scroll_id = None
    page = 0

    while True:
        params = {"catalogId": CATALOG_ID}
        if scroll_id:
            params["scrollId"] = scroll_id
        response = requests.get(f"{PIM_API_URL}/product/scroll", headers=headers, params=params, timeout=60)
        if response.status_code != 200:
            raise RuntimeError(f"Ошибка scroll ({response.status_code}): {response.text[:200]}")
        data = response.json().get("data", {})
        products = data.get("products") or data.get("productElasticDtos") or []
        if not products:
            break

        page += 1
        print(f"📄 Страница {page}: товаров {len(products)}, всего в карте {len(code_map)}")

        for item in products:
            code = normalize_code(item.get("articul"))
            if not code:
                continue
            pim_id = item.get("id")
            if code not in code_map:
                code_map[code] = pim_id
            else:
                duplicates[code].append(pim_id)

        scroll_id = data.get("scrollId")
        if not scroll_id:
            break

    if duplicates:
        print(f"⚠️ Найдены дубликаты code_1c в PIM: {len(duplicates)} значений")
    print(f"✅ Загрузка завершена. Всего code_1c в PIM: {len(code_map)}")
    return code_map, duplicates


def get_rows_to_update(client):
    """Получить все записи из Supabase, которые нужно обновить"""
    rows = []
    offset = 0
    while True:
        response = (
            client.table(TABLE_NAME)
            .select("id, code_1c, article")
            .filter("pim_product_id", "is", "null")
            .range(offset, offset + BATCH_SIZE - 1)
            .execute()
        )
        batch = response.data or []
        if not batch:
            break
        rows.extend(batch)
        offset += BATCH_SIZE
    return rows


def prepare_updates(rows, code_map, duplicates):
    """Подготовить список обновлений"""
    updates = {}
    skipped = 0
    missing = 0
    
    for row in rows:
        code = normalize_code(row.get("code_1c") or row.get("article"))
        if not code:
            skipped += 1
            continue
        if code in duplicates:
            skipped += 1
            continue
        pim_id = code_map.get(code)
        if not pim_id:
            missing += 1
            continue
        updates[row["id"]] = {"id": row["id"], "pim_product_id": pim_id}
    
    return list(updates.values()), skipped, missing


def main():
    ensure_settings()
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    token = get_token()
    
    print("📥 Загрузка товаров из PIM...")
    code_map, duplicates = fetch_pim_codes(token)
    
    print("📋 Поиск записей для обновления в Supabase...")
    rows = get_rows_to_update(client)
    print(f"✅ Найдено {len(rows)} записей без pim_product_id")
    
    print("🔍 Подготовка обновлений...")
    updates, skipped, missing = prepare_updates(rows, code_map, duplicates)
    print(f"✅ Готово к обновлению: {len(updates)} записей")
    
    if not updates:
        print("✅ Нет записей для обновления")
        return
    
    print(f"💾 Обновление записей пачками по {UPSERT_SIZE}...")
    updated = 0
    for i in range(0, len(updates), UPSERT_SIZE):
        batch = updates[i:i + UPSERT_SIZE]
        client.table(TABLE_NAME).upsert(batch, on_conflict="id").execute()
        updated += len(batch)
        print(f"✅ Обновлено: {updated}/{len(updates)}")
        if UPDATE_PAUSE:
            time.sleep(UPDATE_PAUSE)
    
    print(
        f"\nГотово. Обновлено: {updated}, пропущено: {skipped}, не найдены в PIM: {missing}, "
        f"дубликаты в PIM: {len(duplicates)}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"❌ Критическая ошибка: {exc}")

