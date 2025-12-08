#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обновляет поле productGroupId в PIM на основании признака матрицы из таблицы products.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import aiohttp
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PIM_API_URL = (os.getenv("PIM_API_URL") or "").rstrip("/")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")
TABLE_NAME = "products"
BATCH_SIZE = int(os.getenv("MATRIX_BATCH_SIZE", "500"))
CONCURRENT = int(os.getenv("MATRIX_CONCURRENT", "50"))
UPSERT_SIZE = int(os.getenv("MATRIX_UPSERT_SIZE", "500"))
DRY_RUN = os.getenv("MATRIX_DRY_RUN", "").lower() == "true"
MATRIX_FILE = Path(__file__).resolve().parents[1] / "data" / "matrix_groups.json"


def require_settings():
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
        raise SystemExit(f"❌ Отсутствуют переменные окружения: {', '.join(missing)}")


def normalize(value):
    if not value:
        return None
    return " ".join(value.strip().split()).lower()


def load_matrix_map(path):
    with open(path, "r", encoding="utf-8") as file:
        raw = json.load(file)
    return {
        normalize(name): {"id": data["id"], "header": data.get("header", name)}
        for name, data in raw.items()
    }


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


async def fetch_product(session, token, product_id):
    """Загрузить товар из PIM"""
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


def get_rows_to_update(client):
    """Получить все записи с id и matrix, где is_matrix_to_pim = false"""
    rows = []
    offset = 0
    while True:
        response = (
            client.table(TABLE_NAME)
            .select("id,product_name,matrix")
            .eq("is_matrix_to_pim", False)
            .range(offset, offset + BATCH_SIZE - 1)
            .execute()
        )
        batch = response.data or []
        if not batch:
            break
        filtered = [r for r in batch if r.get("id") and r.get("matrix")]
        rows.extend(filtered)
        offset += BATCH_SIZE
    return rows


def prepare_updates(rows, matrix_map):
    """Подготовить список обновлений: (supabase_id, pim_id, target_group_id)"""
    updates = []
    for row in rows:
        raw_matrix = normalize(row.get("matrix"))
        pim_id = row.get("id")
        if not raw_matrix or raw_matrix not in matrix_map:
            continue
        if not pim_id:
            continue
        try:
            pim_id = int(pim_id)
            target_group_id = matrix_map[raw_matrix]["id"]
            updates.append((row["id"], pim_id, target_group_id))
        except (TypeError, ValueError):
            continue
    return updates


async def process_product(session, token_ref, semaphore, supabase_id, pim_id, target_group_id, client):
    """Обработать один товар"""
    async with semaphore:
        token = token_ref[0]
        try:
            fetch_result = await fetch_product(session, token, pim_id)
            if not fetch_result:
                return {"id": supabase_id, "status": "error"}
            result, token = fetch_result
            token_ref[0] = token
            if not result:
                return {"id": supabase_id, "status": "error"}
            
            current_group = result.get("productGroupId")
            if current_group == target_group_id:
                return {"id": supabase_id, "status": "already_ok"}
            
            result["productGroupId"] = target_group_id
            
            if DRY_RUN:
                return {"id": supabase_id, "status": "updated"}
            
            success, token = await update_product(session, token, pim_id, result)
            token_ref[0] = token
            if success:
                return {"id": supabase_id, "status": "updated"}
            return {"id": supabase_id, "status": "error"}
        except Exception as e:
            return {"id": supabase_id, "status": "error", "error": str(e)}


async def main():
    require_settings()
    matrix_map = load_matrix_map(MATRIX_FILE)
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("📋 Загрузка записей из Supabase...")
    rows = get_rows_to_update(client)
    print(f"✅ Найдено {len(rows)} записей для обновления")

    print("🔍 Подготовка обновлений...")
    updates = prepare_updates(rows, matrix_map)
    print(f"✅ Готово к обработке: {len(updates)} товаров")

    if not updates:
        print("✅ Нет товаров для обновления")
        return

    async with aiohttp.ClientSession() as session:
        token = await get_pim_token(session)
        token_ref = [token]
        semaphore = asyncio.Semaphore(CONCURRENT)
        
        stats = {"updated": 0, "already_ok": 0, "errors": 0}
        updated_ids = []
        successfully_updated_pim_ids = []
        
        print(f"📥 Обработка {len(updates)} товаров (параллельно {CONCURRENT})...")
        tasks = [
            process_product(session, token_ref, semaphore, supabase_id, pim_id, target_group_id, client)
            for supabase_id, pim_id, target_group_id in updates
        ]
        
        for idx, task in enumerate(asyncio.as_completed(tasks), 1):
            result = await task
            if result:
                status = result.get("status")
                if status == "updated":
                    stats["updated"] += 1
                    updated_ids.append(result["id"])
                    # Находим PIM ID для этого товара
                    for supabase_id, pim_id, _ in updates:
                        if supabase_id == result["id"]:
                            successfully_updated_pim_ids.append(pim_id)
                            break
                elif status == "already_ok":
                    stats["already_ok"] += 1
                    updated_ids.append(result["id"])
                else:
                    stats["errors"] += 1
                
                if idx % 100 == 0:
                    print(f"✅ Обработано: {idx}/{len(updates)} | Обновлено: {stats['updated']} | Ошибок: {stats['errors']}")
        
        if updated_ids and not DRY_RUN:
            print(f"💾 Обновление флагов в Supabase ({len(updated_ids)} записей)...")
            for i in range(0, len(updated_ids), UPSERT_SIZE):
                batch_ids = updated_ids[i:i + UPSERT_SIZE]
                client.table(TABLE_NAME).update({"is_matrix_to_pim": True}).in_("id", batch_ids).execute()
                print(f"✅ Обновлено флагов: {min(i + UPSERT_SIZE, len(updated_ids))}/{len(updated_ids)}")

    print(
        f"\nГотово. Обновлено: {stats['updated']}, уже правильные: {stats['already_ok']}, "
        f"ошибок: {stats['errors']}"
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"❌ Критическая ошибка: {exc}")
        sys.exit(1)

