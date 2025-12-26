#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экспорт связей товаров с каталогами из PIM.
Получает все товары и их привязки к категориям каталога.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any

import httpx
from dotenv import load_dotenv

# Устанавливаем UTF-8 для Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

BASE_URL = os.getenv("PIM_API_URL", "").rstrip("/")
API_PREFIX = "/api/v1"
LOGIN = os.getenv("PIM_LOGIN")
PASSWORD = os.getenv("PIM_PASSWORD")
CATALOG_ID = int(os.getenv("PIM_PRODUCT_CATALOG", "21"))
OUTPUT_FILE = os.getenv("PIM_PRODUCT_CATALOG_OUTPUT", "data/product_catalog_links.json")
HTTP_TIMEOUT = float(os.getenv("PIM_HTTP_TIMEOUT", "30"))
HTTP_LIMITS = httpx.Limits(max_connections=40, max_keepalive_connections=20)
CONCURRENCY = int(os.getenv("PIM_PRODUCT_CONCURRENCY", "50"))


def ensure_env() -> None:
    """Проверка наличия обязательных переменных окружения."""
    if not BASE_URL or not LOGIN or not PASSWORD:
        raise RuntimeError("Укажите PIM_API_URL, PIM_LOGIN, PIM_PASSWORD в .env")


def build_url(path: str) -> str:
    """Построение полного URL для API запроса."""
    base = BASE_URL.rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    if base.endswith(API_PREFIX) and path.startswith(API_PREFIX):
        path = path[len(API_PREFIX):] or "/"
    return f"{base}{path}"


async def api_call(client: httpx.AsyncClient, method: str, path: str, **kwargs) -> Any:
    """Универсальный метод для API запросов."""
    resp = await client.request(method, build_url(path), **kwargs)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("success") is False:
        raise RuntimeError(data.get("message") or f"Ошибка API {path}")
    return data.get("data", data)


async def fetch_token(client: httpx.AsyncClient) -> str:
    """Получение токена авторизации."""
    payload = {"login": LOGIN, "password": PASSWORD, "remember": True}
    for path in ("/sign-in/", "/api/v1/sign-in/"):
        try:
            data = await api_call(client, "POST", path, json=payload)
            token = data.get("access", {}).get("token")
            if token:
                print("✅ Авторизация успешна")
                return token
        except httpx.HTTPError:
            continue
    raise RuntimeError("Авторизация PIM не удалась")


async def fetch_product_ids(client: httpx.AsyncClient) -> list[int]:
    """Получение всех ID товаров через scroll API."""
    print("📥 Получение списка товаров...")
    
    ids: set[int] = set()
    scroll_id = None
    page = 0
    
    while True:
        params: dict[str, Any] = {"catalogId": CATALOG_ID}
        if scroll_id:
            params["scrollId"] = scroll_id
        
        try:
            data = await api_call(client, "GET", "/api/v1/product/scroll", params=params)
        except Exception as e:
            print(f"⚠️  Ошибка при получении страницы {page}: {e}")
            break
        
        products = data.get("products") or data.get("productElasticDtos") or []
        if not products:
            break
        
        new_ids = {prod.get("id") for prod in products if prod.get("id")}
        ids.update(new_ids)
        
        page += 1
        print(f"   📄 Страница {page}: +{len(new_ids)} товаров (всего: {len(ids)})")
        
        scroll_id = data.get("scrollId")
        if not scroll_id:
            break
    
    print(f"✅ Найдено {len(ids)} товаров в каталоге {CATALOG_ID}")
    return sorted(ids)


def extract_catalog_links(product_data: dict) -> list[dict]:
    """
    Извлечение связей товара с каталогами.
    
    Возвращает список словарей с информацией о привязках.
    """
    product_id = product_data.get("id")
    if not product_id:
        return []
    
    links = []
    
    # Основной каталог
    catalog = product_data.get("catalog")
    if catalog and catalog.get("id"):
        links.append({
            "product_id": product_id,
            "catalog_id": catalog["id"],
            "catalog_sync_uid": catalog.get("syncUid"),
            "catalog_header": catalog.get("header"),
            "is_primary": True,
            "sort_order": 0,
        })
    
    # Дополнительные каталоги
    catalogs_additional = product_data.get("catalogs") or []
    for idx, cat in enumerate(catalogs_additional, start=1):
        if cat and cat.get("id"):
            links.append({
                "product_id": product_id,
                "catalog_id": cat["id"],
                "catalog_sync_uid": cat.get("syncUid"),
                "catalog_header": cat.get("header"),
                "is_primary": False,
                "sort_order": idx,
            })
    
    return links


async def fetch_product_catalogs(
    client: httpx.AsyncClient,
    product_ids: list[int]
) -> tuple[list[dict], list[dict]]:
    """
    Получение информации о привязках товаров к каталогам.
    
    Returns:
        Tuple[links, products] - список связей и список товаров с базовой инфо
    """
    semaphore = asyncio.Semaphore(CONCURRENCY)
    all_links: list[dict] = []
    all_products: list[dict] = []
    
    async def fetch_one(pid: int):
        async with semaphore:
            try:
                data = await api_call(client, "GET", f"/api/v1/product/{pid}")
                
                # Извлекаем связи с каталогами
                links = extract_catalog_links(data)
                if links:
                    all_links.extend(links)
                
                # Сохраняем базовую информацию о товаре
                product_info = {
                    "id": data.get("id"),
                    "header": data.get("header"),
                    "articul": data.get("articul"),
                    "sync_uid": data.get("syncUid"),
                    "enabled": data.get("enabled"),
                    "deleted": data.get("deleted"),
                    "primary_catalog_id": data.get("catalog", {}).get("id"),
                    "additional_catalogs_count": len(data.get("catalogs", [])),
                }
                all_products.append(product_info)
                
                print(f"✅ [{len(all_products)}/{len(product_ids)}] Товар {pid}: {len(links)} связей")
                
            except Exception as exc:
                print(f"❌ Ошибка товара {pid}: {exc}")
    
    print(f"\n📥 Получение данных {len(product_ids)} товаров...")
    await asyncio.gather(*(fetch_one(pid) for pid in product_ids))
    
    return all_links, all_products


def calculate_statistics(links: list[dict], products: list[dict]) -> dict:
    """Расчет статистики по связям товаров с каталогами."""
    total_links = len(links)
    total_products = len(products)
    primary_links = sum(1 for link in links if link.get("is_primary"))
    additional_links = total_links - primary_links
    
    # Товары без категорий
    products_with_links = len({link["product_id"] for link in links})
    products_without_links = total_products - products_with_links
    
    # Распределение товаров по каталогам
    catalog_distribution: dict[int, int] = {}
    for link in links:
        cat_id = link["catalog_id"]
        catalog_distribution[cat_id] = catalog_distribution.get(cat_id, 0) + 1
    
    # Топ-10 каталогов по количеству товаров
    top_catalogs = sorted(
        catalog_distribution.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    return {
        "total_products": total_products,
        "total_links": total_links,
        "primary_links": primary_links,
        "additional_links": additional_links,
        "products_with_links": products_with_links,
        "products_without_links": products_without_links,
        "unique_catalogs": len(catalog_distribution),
        "avg_catalogs_per_product": round(total_links / total_products, 2) if total_products > 0 else 0,
        "top_catalogs": [{"catalog_id": cat_id, "product_count": count} for cat_id, count in top_catalogs],
    }


def save_payload(links: list[dict], products: list[dict]) -> None:
    """Сохранение результата в JSON файл."""
    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    
    statistics = calculate_statistics(links, products)
    
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": "COMPO PIM API",
        "catalog_id": CATALOG_ID,
        "statistics": statistics,
        "links": links,
        "products": products,
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Связи товаров с каталогами сохранены в {OUTPUT_FILE}")
    print(f"📊 Статистика:")
    print(f"   • Всего товаров: {statistics['total_products']}")
    print(f"   • Всего связей: {statistics['total_links']}")
    print(f"   • Основных категорий: {statistics['primary_links']}")
    print(f"   • Дополнительных категорий: {statistics['additional_links']}")
    print(f"   • Товаров без категорий: {statistics['products_without_links']}")
    print(f"   • Уникальных каталогов: {statistics['unique_catalogs']}")
    print(f"   • Среднее категорий на товар: {statistics['avg_catalogs_per_product']}")


async def main():
    """Основная функция."""
    ensure_env()
    
    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
        limits=HTTP_LIMITS,
        follow_redirects=True,
    ) as client:
        token = await fetch_token(client)
        client.headers["Authorization"] = f"Bearer {token}"
        
        # Получаем список товаров
        product_ids = await fetch_product_ids(client)
        
        # Получаем связи товаров с каталогами
        links, products = await fetch_product_catalogs(client, product_ids)
        
        # Сохраняем результат
        save_payload(links, products)


if __name__ == "__main__":
    asyncio.run(main())

