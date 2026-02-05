#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экспорт полной информации о продуктах из PIM с features.
Использует /product/scroll API, который возвращает полные данные в productElasticDtos.

Структура выходного файла:
[
  {
    "id": 9724,
    "header": "Грунт 25л Здоровая земля (5)",
    "articul": "144314",
    "catalogId": 696,
    "templateId": 898,
    "templateHeader": "Грунты универсальные",
    "catalogHeader": "Грунт",
    "features": [
      {
        "id": 14147,
        "header": "Мера кислотности, pH",
        "groupId": 906,
        "groupHeader": "Технические характеристики",
        "code": "...",
        "type": 4,
        "gold": false,
        "values": [...]
      }
    ],
    ...остальные поля...
  }
]
"""

import asyncio
import json
import os
from datetime import datetime, UTC
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("PIM_API_URL", "").rstrip("/")
API_PREFIX = "/api/v1"
LOGIN = os.getenv("PIM_LOGIN")
PASSWORD = os.getenv("PIM_PASSWORD")
CATALOG_ID = int(os.getenv("PIM_PRODUCT_CATALOG", "21"))  # По умолчанию каталог 21
OUTPUT_FILE = os.getenv("PIM_FULL_PRODUCTS_OUTPUT", "data/full_products_export.json")
HTTP_TIMEOUT = float(os.getenv("PIM_HTTP_TIMEOUT", "30"))
HTTP_LIMITS = httpx.Limits(max_connections=40, max_keepalive_connections=20)


def ensure_env() -> None:
    """Проверка наличия необходимых переменных окружения."""
    if not BASE_URL or not LOGIN or not PASSWORD:
        raise RuntimeError("Задайте PIM_API_URL, PIM_LOGIN, PIM_PASSWORD в .env")


def build_url(path: str) -> str:
    """Построение полного URL для API запроса с учетом дублирования /api/v1."""
    base = BASE_URL.rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    # Избегаем дублирования /api/v1/api/v1
    if base.endswith(API_PREFIX) and path.startswith(API_PREFIX):
        path = path[len(API_PREFIX):] or "/"
    return f"{base}{path}"


async def api_call(client: httpx.AsyncClient, method: str, path: str, **kwargs) -> Any:
    """Универсальный метод для API запросов."""
    url = build_url(path)
    resp = await client.request(method, url, **kwargs)
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
                print("[OK] Авторизация успешна")
                return token
        except httpx.HTTPError:
            continue
    raise RuntimeError("Авторизация PIM не удалась")


async def fetch_all_products_from_scroll(client: httpx.AsyncClient) -> list[dict]:
    """
    Получение ВСЕХ товаров через scroll API.
    API /product/scroll УЖЕ возвращает полные данные в productElasticDtos!
    Можно фильтровать по catalogId через переменную окружения.
    """
    print("[>>] Получение товаров с характеристиками через scroll API...")
    
    all_products: list[dict] = []
    scroll_id = None
    page = 0
    
    while True:
        params: dict[str, Any] = {}
        
        # Если указан каталог - фильтруем по нему
        if CATALOG_ID > 0:
            params["catalogId"] = CATALOG_ID
        
        if scroll_id:
            params["scrollId"] = scroll_id
        
        try:
            data = await api_call(client, "GET", "/api/v1/product/scroll", params=params)
        except Exception as e:
            print(f"[!] Ошибка при получении страницы {page}: {e}")
            break
        
        # API возвращает полные данные с features в productElasticDtos!
        products = data.get("productElasticDtos") or data.get("products") or []
        if not products:
            break
        
        all_products.extend(products)
        
        page += 1
        total = data.get("total", "?")
        print(f"   [+] Страница {page}: +{len(products)} товаров (всего: {len(all_products)}/{total})")
        
        scroll_id = data.get("scrollId")
        if not scroll_id:
            break
    
    if not all_products:
        raise RuntimeError("Не удалось получить товары")
    
    print(f"[OK] Получено {len(all_products)} товаров с полными данными")
    return all_products


def save_payload(products: list[dict], failed_ids: list[int] = None) -> None:
    """Сохранение результата в JSON файл."""
    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    
    # Сортируем по ID для удобства
    products.sort(key=lambda p: p.get("id", 0))
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(products, fh, ensure_ascii=False, indent=2)
    
    print(f"\n[SAVE] Данные сохранены в {OUTPUT_FILE}")
    print(f"[STAT] Статистика:")
    print(f"   - Всего товаров: {len(products)}")
    
    # Статистика по features
    products_with_features = sum(1 for p in products if p.get("features"))
    total_features = sum(len(p.get("features", [])) for p in products)
    print(f"   - Товаров с характеристиками: {products_with_features}")
    print(f"   - Всего характеристик: {total_features}")
    
    # Статистика по enabled/deleted
    enabled = sum(1 for p in products if p.get("enabled"))
    deleted = sum(1 for p in products if p.get("deleted"))
    print(f"   - Активных: {enabled}")
    print(f"   - Удаленных: {deleted}")
    
    # Статистика по ошибкам
    if failed_ids:
        print(f"\n[!] Не удалось загрузить:")
        print(f"   - Количество: {len(failed_ids)}")
        print(f"   - ID товаров: {failed_ids[:20]}")  # Показываем первые 20
        if len(failed_ids) > 20:
            print(f"   - ... и еще {len(failed_ids) - 20}")
        
        # Сохраняем список проваленных ID в отдельный файл
        failed_file = OUTPUT_FILE.replace(".json", "_failed_ids.json")
        with open(failed_file, "w", encoding="utf-8") as fh:
            json.dump({"failed_ids": failed_ids, "count": len(failed_ids)}, fh, ensure_ascii=False, indent=2)
        print(f"   - Список сохранен в: {failed_file}")


async def main():
    """Основная функция."""
    ensure_env()
    
    print(f"\n>> ЭКСПОРТ ПОЛНЫХ ДАННЫХ ПРОДУКТОВ ИЗ PIM")
    print(f"{'=' * 60}")
    
    if CATALOG_ID > 0:
        print(f">> Фильтр по каталогу: ID={CATALOG_ID}")
    else:
        print(f">> Экспорт ВСЕХ товаров (catalogId не указан)")
    
    print(f">> Выходной файл: {OUTPUT_FILE}")
    print(f">> Данные извлекаются напрямую из product/scroll API\n")
    
    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
        limits=HTTP_LIMITS,
        follow_redirects=True,
    ) as client:
        # Авторизация
        token = await fetch_token(client)
        client.headers["Authorization"] = f"Bearer {token}"
        
        # Получение ВСЕХ товаров сразу (API возвращает полные данные!)
        products = await fetch_all_products_from_scroll(client)
        
        print(f"\n[OK] Обработка завершена:")
        print(f"   - Получено товаров: {len(products)}")
        
        # Сохранение результата (без failed_ids, так как нет дополнительных запросов)
        save_payload(products, failed_ids=[])
        
        print(f"\n{'=' * 60}")
        print(f"[DONE] Экспорт завершен успешно!")
        print(f"{'=' * 60}\n")


if __name__ == "__main__":
    asyncio.run(main())
