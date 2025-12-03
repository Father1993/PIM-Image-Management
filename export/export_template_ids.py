#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Получение всех ID шаблонов и сохранение их в ID-temp.json.
Скрипт заменяет ручное наполнение файла перед экспортом шаблонов.
"""

import asyncio
import json
import os

import httpx
from dotenv import load_dotenv


load_dotenv()

PIM_API_URL = os.getenv("PIM_API_URL", "").rstrip("/")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")

HTTPX_TIMEOUT = 60.0
HTTPX_LIMITS = httpx.Limits(max_keepalive_connections=10, max_connections=20)
MAX_RETRIES = 3
RETRY_DELAY = 2


async def authenticate() -> str:
    """Возвращает Bearer-токен из PIM API."""
    payload = {"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
    async with httpx.AsyncClient(timeout=HTTPX_TIMEOUT, http2=False, limits=HTTPX_LIMITS) as client:
        for path in ("/sign-in/", "/api/v1/sign-in/"):
            try:
                resp = await client.post(f"{PIM_API_URL}{path}", json=payload)
                if resp.status_code == 200:
                    token = resp.json().get("data", {}).get("access", {}).get("token")
                    if token:
                        return token
            except httpx.RequestError:
                pass
    raise RuntimeError("Не удалось авторизоваться в PIM API")


async def fetch_template_ids(token: str, catalog_id: int = 21) -> list[dict]:
    """Получает уникальные ID шаблонов из товаров через scroll API."""
    headers = {"Authorization": f"Bearer {token}"}
    template_ids: set[int] = set()
    scroll_id = None
    total_processed = 0
    
    print(f"📥 Получаем ID шаблонов из товаров каталога {catalog_id}...")
    
    client = httpx.AsyncClient(
        headers=headers,
        timeout=HTTPX_TIMEOUT,
        http2=False,  # Отключаем HTTP/2 для стабильности
        limits=HTTPX_LIMITS
    )
    
    try:
        while True:
            params = {"catalogId": catalog_id}
            if scroll_id:
                params["scrollId"] = scroll_id
            
            url = f"{PIM_API_URL}/product/scroll"
            
            # Повторные попытки при ошибках соединения
            resp = None
            for attempt in range(MAX_RETRIES):
                try:
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    break
                except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadTimeout) as e:
                    if attempt < MAX_RETRIES - 1:
                        print(f"  ⚠️ Ошибка соединения (попытка {attempt + 1}/{MAX_RETRIES}), повтор через {RETRY_DELAY}с...")
                        await asyncio.sleep(RETRY_DELAY)
                        # Пересоздаем клиент при ошибке соединения
                        await client.aclose()
                        client = httpx.AsyncClient(
                            headers=headers,
                            timeout=HTTPX_TIMEOUT,
                            http2=False,
                            limits=HTTPX_LIMITS
                        )
                    else:
                        print(f"  ❌ Не удалось получить данные после {MAX_RETRIES} попыток")
                        return [{"id": tid} for tid in sorted(template_ids)]
            
            if not resp:
                break
            
            data = resp.json()
            if not data.get("success"):
                break
            
            products = data.get("data", {}).get("products", []) or data.get("data", {}).get("productElasticDtos", [])
            if not products:
                break
            
            for product in products:
                template_id = product.get("templateId")
                if template_id:
                    template_ids.add(template_id)
            
            total_processed += len(products)
            print(f"  Обработано товаров: {total_processed} (в партии: {len(products)}), найдено шаблонов: {len(template_ids)}")
            
            scroll_id = data.get("data", {}).get("scrollId")
            if not scroll_id:
                break
    finally:
        await client.aclose()
    
    return [{"id": tid} for tid in sorted(template_ids)]


async def main():
    if not PIM_API_URL:
        raise RuntimeError("Переменная PIM_API_URL не задана")

    token = await authenticate()
    template_ids = await fetch_template_ids(token, catalog_id=21)

    if not template_ids:
        raise RuntimeError("Не удалось получить список ID шаблонов")

    with open("ID-temp.json", "w", encoding="utf-8") as fh:
        json.dump(template_ids, fh, ensure_ascii=False, indent=2)

    print(f"✅ Сохранено {len(template_ids)} шаблонов в ID-temp.json")


if __name__ == "__main__":
    asyncio.run(main())

