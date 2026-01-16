#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экспорт дерева каталога с товарами из PIM.
Создает JSON файл с полной структурой каталога и привязанными товарами.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any

import httpx
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

BASE_URL = os.getenv("PIM_API_URL", "").rstrip("/")
API_PREFIX = "/api/v1"
LOGIN = os.getenv("PIM_LOGIN")
PASSWORD = os.getenv("PIM_PASSWORD")
CATALOG_ID = int(os.getenv("PIM_PRODUCT_CATALOG", "21"))
OUTPUT_FILE = os.getenv("PIM_CATALOG_TREE_OUTPUT", "data/catalog_tree_with_products.json")
HTTP_TIMEOUT = float(os.getenv("PIM_HTTP_TIMEOUT", "30"))
HTTP_LIMITS = httpx.Limits(max_connections=40, max_keepalive_connections=20)
CONCURRENCY = int(os.getenv("PIM_PRODUCT_CONCURRENCY", "50"))


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


async def fetch_catalog_tree(client: httpx.AsyncClient) -> list[dict]:
    """Получение полного дерева каталогов."""
    print("📥 Получение дерева каталогов...")
    data = await api_call(client, "GET", "/api/v1/catalog")
    if isinstance(data, list):
        return data
    raise RuntimeError("Неожиданный формат ответа от /api/v1/catalog")


def find_catalog_by_id(tree: list[dict], catalog_id: int) -> dict | None:
    """Поиск каталога по ID в дереве."""
    for catalog in tree:
        if catalog.get("id") == catalog_id:
            return catalog
        children = catalog.get("children", [])
        if children:
            found = find_catalog_by_id(children, catalog_id)
            if found:
                return found
    return None


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


async def fetch_product_data(client: httpx.AsyncClient, product_ids: list[int]) -> dict[int, dict]:
    """Получение данных товаров с их привязками к каталогам."""
    semaphore = asyncio.Semaphore(CONCURRENCY)
    products: dict[int, dict] = {}
    
    async def fetch_one(pid: int):
        async with semaphore:
            try:
                data = await api_call(client, "GET", f"/api/v1/product/{pid}")
                
                # Извлекаем связи с каталогами
                catalog_ids = []
                primary_catalog_id = None
                
                catalog = data.get("catalog")
                if catalog and catalog.get("id"):
                    primary_catalog_id = catalog["id"]
                    catalog_ids.append(primary_catalog_id)
                
                catalogs_additional = data.get("catalogs") or []
                for cat in catalogs_additional:
                    if cat and cat.get("id"):
                        catalog_ids.append(cat["id"])
                
                products[pid] = {
                    "id": data.get("id"),
                    "header": data.get("header"),
                    "articul": data.get("articul"),
                    "sync_uid": data.get("syncUid"),
                    "enabled": data.get("enabled"),
                    "deleted": data.get("deleted"),
                    "primary_catalog_id": primary_catalog_id,
                    "catalog_ids": catalog_ids,
                }
                
                if len(products) % 100 == 0:
                    print(f"✅ Обработано {len(products)}/{len(product_ids)} товаров")
                
            except Exception as exc:
                print(f"❌ Ошибка товара {pid}: {exc}")
    
    print(f"\n📥 Получение данных {len(product_ids)} товаров...")
    await asyncio.gather(*(fetch_one(pid) for pid in product_ids))
    
    return products


def build_catalog_tree_with_products(
    catalog_tree: list[dict],
    products: dict[int, dict],
    target_catalog_id: int
) -> dict:
    """Построение дерева каталога с товарами."""
    
    def add_products_to_catalog(catalog: dict, all_products: dict[int, dict]) -> dict:
        """Рекурсивное добавление товаров в каталог."""
        catalog_id = catalog.get("id")
        
        # Находим товары для этого каталога
        catalog_products = [
            {
                "id": p["id"],
                "header": p["header"],
                "articul": p["articul"],
                "sync_uid": p["sync_uid"],
                "enabled": p["enabled"],
                "is_primary": p["primary_catalog_id"] == catalog_id,
            }
            for p in all_products.values()
            if catalog_id in p["catalog_ids"]
        ]
        
        # Обрабатываем детей
        children = catalog.get("children", [])
        processed_children = [
            add_products_to_catalog(child, all_products)
            for child in children
        ]
        
        # Формируем результат
        return {
            "id": catalog.get("id"),
            "header": catalog.get("header"),
            "syncUid": catalog.get("syncUid"),
            "parentId": catalog.get("parentId"),
            "level": catalog.get("level"),
            "lastLevel": catalog.get("lastLevel"),
            "enabled": catalog.get("enabled"),
            "deleted": catalog.get("deleted"),
            "productCountPim": catalog.get("productCountPim", 0),
            "lft": catalog.get("lft"),
            "rgt": catalog.get("rgt"),
            "products": catalog_products,
            "products_count": len(catalog_products),
            "children": processed_children,
        }
    
    # Находим нужный каталог в дереве
    target_catalog = find_catalog_by_id(catalog_tree, target_catalog_id)
    if not target_catalog:
        raise RuntimeError(f"Каталог с ID {target_catalog_id} не найден")
    
    # Строим дерево с товарами
    return add_products_to_catalog(target_catalog, products)


def calculate_statistics(tree: dict, products: dict[int, dict]) -> dict:
    """Расчет статистики."""
    
    def count_catalogs(catalog: dict) -> tuple[int, int, int]:
        """Подсчет каталогов рекурсивно."""
        total = 1
        with_products = 1 if catalog.get("products_count", 0) > 0 else 0
        leaf = 1 if catalog.get("lastLevel") else 0
        
        for child in catalog.get("children", []):
            t, wp, l = count_catalogs(child)
            total += t
            with_products += wp
            leaf += l
        
        return total, with_products, leaf
    
    total_catalogs, catalogs_with_products, leaf_catalogs = count_catalogs(tree)
    
    return {
        "total_catalogs": total_catalogs,
        "catalogs_with_products": catalogs_with_products,
        "leaf_catalogs": leaf_catalogs,
        "total_products": len(products),
        "max_depth": tree.get("level", 0),
    }


def save_payload(tree: dict, products: dict[int, dict]) -> None:
    """Сохранение результата в JSON файл."""
    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    
    statistics = calculate_statistics(tree, products)
    
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": "COMPO PIM API",
        "catalog_id": CATALOG_ID,
        "statistics": statistics,
        "tree": tree,
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Дерево каталога с товарами сохранено в {OUTPUT_FILE}")
    print(f"📊 Статистика:")
    print(f"   • Всего каталогов: {statistics['total_catalogs']}")
    print(f"   • Каталогов с товарами: {statistics['catalogs_with_products']}")
    print(f"   • Конечных каталогов: {statistics['leaf_catalogs']}")
    print(f"   • Всего товаров: {statistics['total_products']}")


async def main():
    """Основная функция."""
    if not BASE_URL or not LOGIN or not PASSWORD:
        raise RuntimeError("Укажите PIM_API_URL, PIM_LOGIN, PIM_PASSWORD в .env")
    
    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
        limits=HTTP_LIMITS,
        follow_redirects=True,
    ) as client:
        token = await fetch_token(client)
        client.headers["Authorization"] = f"Bearer {token}"
        
        # Получаем дерево каталогов
        catalog_tree = await fetch_catalog_tree(client)
        print(f"✅ Получено дерево каталогов")
        
        # Получаем товары
        product_ids = await fetch_product_ids(client)
        
        # Получаем данные товаров
        products = await fetch_product_data(client, product_ids)
        print(f"✅ Получено данных о {len(products)} товарах")
        
        # Строим дерево с товарами
        tree = build_catalog_tree_with_products(catalog_tree, products, CATALOG_ID)
        print(f"✅ Построено дерево каталога с товарами")
        
        # Сохраняем результат
        save_payload(tree, products)


if __name__ == "__main__":
    asyncio.run(main())
