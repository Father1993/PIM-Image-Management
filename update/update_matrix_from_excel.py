#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обновляет признак матрицы в PIM для товаров из Excel файла.
"""

import asyncio
import json
import os
import pandas as pd
import re
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
EXCEL_FILE = "products_to_update_matrix_20251208_165911.xlsx"
MATRIX_FILE = Path(__file__).resolve().parents[1] / "data" / "matrix_groups.json"
CONCURRENT = 50


def normalize(value):
    if not value:
        return None
    return " ".join(str(value).strip().split()).lower()


def find_matrix_match(value, matrix_map):
    """Найти совпадение матрицы"""
    if not value:
        return None
    
    normalized = normalize(value)
    if normalized in matrix_map:
        return matrix_map[normalized]
    
    base_value = re.sub(r'\([^)]*\)', '', value).strip()
    base_normalized = normalize(base_value)
    
    for key, data in matrix_map.items():
        key_base = re.sub(r'\([^)]*\)', '', key).strip()
        if normalize(key_base) == base_normalized:
            return data
    
    return None


def load_matrix_map(path):
    """Загрузить маппинг матриц"""
    with open(path, "r", encoding="utf-8") as file:
        raw = json.load(file)
    
    matrix_map = {}
    for name, data in raw.items():
        normalized = normalize(name)
        matrix_map[normalized] = {"id": data["id"], "header": data.get("header", name)}
        
        if '(' in name:
            base_name = re.sub(r'\([^)]*\)', '', name).strip()
            base_normalized = normalize(base_name)
            if base_normalized and base_normalized not in matrix_map:
                matrix_map[base_normalized] = {"id": data["id"], "header": data.get("header", name)}
    
    return matrix_map


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


async def process_product(session, token_ref, semaphore, pim_id, matrix_value, matrix_map):
    """Обработать один товар"""
    async with semaphore:
        token = token_ref[0]
        try:
            matrix_data = find_matrix_match(matrix_value, matrix_map)
            if not matrix_data:
                return {"id": pim_id, "status": "unknown_matrix", "matrix": matrix_value}
            
            fetch_result = await fetch_product(session, token, pim_id)
            if not fetch_result:
                return {"id": pim_id, "status": "error"}
            
            result, token = fetch_result
            token_ref[0] = token
            
            if not result:
                return {"id": pim_id, "status": "error"}
            
            target_group_id = matrix_data["id"]
            if result.get("productGroupId") == target_group_id:
                return {"id": pim_id, "status": "already_ok"}
            
            result["productGroupId"] = target_group_id
            
            success, token = await update_product(session, token, pim_id, result)
            token_ref[0] = token
            
            if success:
                return {"id": pim_id, "status": "updated"}
            return {"id": pim_id, "status": "error"}
        except Exception as e:
            return {"id": pim_id, "status": "error", "error": str(e)}


async def main():
    print("📥 Загрузка Excel файла...")
    df = pd.read_excel(EXCEL_FILE)
    print(f"✅ Загружено {len(df)} товаров")
    
    print("📋 Загрузка матриц из Supabase...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    pim_ids = df["id"].dropna().astype(int).tolist()
    
    products_data = {}
    for i in range(0, len(pim_ids), 500):
        batch = pim_ids[i:i + 500]
        response = client.table("products").select("id,matrix").in_("id", batch).execute()
        for row in (response.data or []):
            if row.get("matrix"):
                products_data[row["id"]] = row["matrix"]
    
    print(f"✅ Найдено {len(products_data)} товаров с матрицей")
    
    print("📚 Загрузка маппинга матриц...")
    matrix_map = load_matrix_map(MATRIX_FILE)
    
    updates = []
    for pim_id in pim_ids:
        matrix_value = products_data.get(pim_id)
        if matrix_value:
            updates.append((pim_id, matrix_value))
    
    print(f"✅ Готово к обработке: {len(updates)} товаров")
    
    if not updates:
        print("✅ Нет товаров для обновления")
        return
    
    async with aiohttp.ClientSession() as session:
        token = await get_pim_token(session)
        token_ref = [token]
        semaphore = asyncio.Semaphore(CONCURRENT)
        
        stats = {"updated": 0, "already_ok": 0, "errors": 0, "unknown_matrix": 0}
        
        print(f"📥 Обработка {len(updates)} товаров...")
        tasks = [
            process_product(session, token_ref, semaphore, pim_id, matrix_value, matrix_map)
            for pim_id, matrix_value in updates
        ]
        
        for idx, task in enumerate(asyncio.as_completed(tasks), 1):
            result = await task
            status = result.get("status")
            if status == "updated":
                stats["updated"] += 1
            elif status == "already_ok":
                stats["already_ok"] += 1
            elif status == "unknown_matrix":
                stats["unknown_matrix"] += 1
                print(f"⚠️  Неизвестная матрица для ID {result['id']}: {result.get('matrix')}")
            else:
                stats["errors"] += 1
            
            if idx % 50 == 0:
                print(f"✅ Обработано: {idx}/{len(updates)} | Обновлено: {stats['updated']} | Ошибок: {stats['errors']}")
    
    print(f"\nГотово. Обновлено: {stats['updated']}, уже правильные: {stats['already_ok']}, "
          f"неизвестные матрицы: {stats['unknown_matrix']}, ошибок: {stats['errors']}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"❌ Критическая ошибка: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

