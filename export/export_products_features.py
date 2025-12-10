#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Экспорт характеристик товаров каталога 21.
Структура: {articul, featureValues[{featureId, value}, ...]}.
"""

import asyncio
import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("PIM_API_URL", "").rstrip("/")
API_PREFIX = "/api/v1"
LOGIN = os.getenv("PIM_LOGIN")
PASSWORD = os.getenv("PIM_PASSWORD")
CATALOG_ID = int(os.getenv("PIM_PRODUCT_CATALOG", "21"))
OUTPUT_FILE = os.getenv("PIM_PRODUCT_OUTPUT", "products_features.json")
HTTP_TIMEOUT = float(os.getenv("PIM_HTTP_TIMEOUT", "30"))
HTTP_LIMITS = httpx.Limits(max_connections=40, max_keepalive_connections=20)
CONCURRENCY = int(os.getenv("PIM_PRODUCT_CONCURRENCY", "80"))


def ensure_env():
    if not BASE_URL or not LOGIN or not PASSWORD:
        raise RuntimeError("Укажите PIM_API_URL, PIM_LOGIN, PIM_PASSWORD в .env")


def build_url(path: str) -> str:
    base = BASE_URL.rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    # избегаем /api/v1/api/v1, если база уже содержит суффикс
    if base.endswith(API_PREFIX) and path.startswith(API_PREFIX):
        path = path[len(API_PREFIX):] or "/"
    return f"{base}{path}"


async def api_call(client: httpx.AsyncClient, method: str, path: str, **kwargs):
    resp = await client.request(method, build_url(path), **kwargs)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("success") is False:
        raise RuntimeError(data.get("message") or f"Ошибка API {url}")
    return data.get("data", data)


async def fetch_token(client: httpx.AsyncClient) -> str:
    payload = {"login": LOGIN, "password": PASSWORD, "remember": True}
    for path in ("/sign-in/", "/api/v1/sign-in/"):
        try:
            data = await api_call(client, "POST", path, json=payload)
            token = data.get("access", {}).get("token")
            if token:
                return token
        except httpx.HTTPError:
            continue
    raise RuntimeError("Авторизация PIM не удалась")


async def fetch_product_ids(client: httpx.AsyncClient) -> list[int]:
    ids: set[int] = set()
    scroll_id = None
    while True:
        params = {"catalogId": CATALOG_ID}
        if scroll_id:
            params["scrollId"] = scroll_id
        data = await api_call(client, "GET", "/api/v1/product/scroll", params=params)
        products = data.get("products") or data.get("productElasticDtos") or []
        if not products:
            break
        ids.update(prod.get("id") for prod in products if prod.get("id"))
        scroll_id = data.get("scrollId")
        if not scroll_id:
            break
    if not ids:
        raise RuntimeError("Не удалось получить ID товаров каталога")
    print(f"📦 Найдено {len(ids)} товаров каталога {CATALOG_ID}")
    return sorted(ids)


def simplify_product(data: dict) -> dict | None:
    articul = data.get("articul")
    feature_values = data.get("featureValues") or []
    simplified: list[dict] = []

    if feature_values:
        for item in feature_values:
            feature_id = item.get("featureId") or item.get("feature", {}).get("id")
            if feature_id is None:
                continue
            simplified.append({"featureId": feature_id, "value": item.get("value")})
    else:
        for feature in data.get("features") or []:
            feature_id = feature.get("id") or feature.get("featureId")
            for value in feature.get("values") or []:
                if feature_id is None:
                    continue
                simplified.append({"featureId": feature_id, "value": value.get("value") or value.get("header")})

    if not articul and not simplified:
        return None

    return {"articul": articul, "featureValues": simplified}


async def fetch_products(client: httpx.AsyncClient, ids: list[int]) -> list[dict]:
    semaphore = asyncio.Semaphore(CONCURRENCY)
    results: list[dict] = []

    async def fetch_one(pid: int):
        async with semaphore:
            try:
                data = await api_call(client, "GET", f"/api/v1/product/{pid}")
                simplified = simplify_product(data)
                if simplified:
                    results.append(simplified)
                    print(f"✅ Товар {pid}")
                else:
                    print(f"⚠️ Товар {pid} без необходимых данных")
            except Exception as exc:  # noqa: BLE001
                print(f"❌ Ошибка товара {pid}: {exc}")

    await asyncio.gather(*(fetch_one(pid) for pid in ids))
    return results


def save_payload(payload: list[dict]):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"💾 Сохранено {len(payload)} товаров в {OUTPUT_FILE}")


async def main():
    ensure_env()
    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
        limits=HTTP_LIMITS,
        follow_redirects=True,
    ) as client:
        token = await fetch_token(client)
        client.headers["Authorization"] = f"Bearer {token}"
        product_ids = await fetch_product_ids(client)
        products = await fetch_products(client, product_ids)
        save_payload(products)


if __name__ == "__main__":
    asyncio.run(main())

