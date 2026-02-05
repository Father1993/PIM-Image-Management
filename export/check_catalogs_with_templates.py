#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для поиска каталогов, содержащих товары с шаблонами.
"""

import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("PIM_API_URL", "").rstrip("/")
API_PREFIX = "/api/v1"
LOGIN = os.getenv("PIM_LOGIN")
PASSWORD = os.getenv("PIM_PASSWORD")


def build_url(path: str) -> str:
    base = BASE_URL.rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    if base.endswith(API_PREFIX) and path.startswith(API_PREFIX):
        path = path[len(API_PREFIX):] or "/"
    return f"{base}{path}"


async def api_call(client, method, path, **kwargs):
    url = build_url(path)
    resp = await client.request(method, url, **kwargs)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("success") is False:
        raise RuntimeError(data.get("message") or f"Ошибка API {path}")
    return data.get("data", data)


async def fetch_token(client):
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


async def check_catalog_products(client, catalog_id, limit=10):
    """Проверяет первые товары каталога на наличие шаблонов."""
    try:
        params = {"catalogId": catalog_id}
        data = await api_call(client, "GET", "/api/v1/product/scroll", params=params)
        products = data.get("products") or data.get("productElasticDtos") or []
        
        # Проверяем первые товары
        products_checked = products[:limit]
        with_templates = sum(1 for p in products_checked if p.get("templateId"))
        
        return {
            "catalog_id": catalog_id,
            "total_products": data.get("total", 0),
            "checked": len(products_checked),
            "with_templates": with_templates
        }
    except Exception as e:
        return None


async def main():
    print("\n🔍 ПОИСК КАТАЛОГОВ С ТОВАРАМИ, ИМЕЮЩИМИ ШАБЛОНЫ")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        token = await fetch_token(client)
        client.headers["Authorization"] = f"Bearer {token}"
        print("✅ Авторизация успешна\n")
        
        # Проверяем популярные каталоги
        print("📊 Проверка каталогов...")
        catalogs_to_check = [0, 21, 696, 826, 1027, 685, 688]  # 0 = все товары
        
        results = []
        for cat_id in catalogs_to_check:
            result = await check_catalog_products(client, cat_id)
            if result:
                results.append(result)
                print(f"   Каталог {result['catalog_id']}: "
                      f"{result['total_products']} товаров, "
                      f"{result['with_templates']}/{result['checked']} с шаблонами")
        
        print(f"\n{'=' * 60}")
        print("💡 РЕКОМЕНДАЦИИ:\n")
        
        best = max(results, key=lambda x: x['with_templates'])
        if best['with_templates'] > 0:
            print(f"   • Используйте каталог {best['catalog_id']} ({best['with_templates']}/{best['checked']} товаров с шаблонами)")
            print(f"   • Или установите PIM_PRODUCT_CATALOG=0 для экспорта ВСЕХ товаров\n")
            print(f"В .env файле:")
            print(f"   PIM_PRODUCT_CATALOG={best['catalog_id'] if best['catalog_id'] != 0 else '0  # все товары'}")
        else:
            print("   ⚠️ Товары с шаблонами не найдены в проверенных каталогах")
            print("   • Попробуйте установить PIM_PRODUCT_CATALOG=0 (все товары)")


if __name__ == "__main__":
    asyncio.run(main())
