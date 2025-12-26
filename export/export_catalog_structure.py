#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экспорт полной структуры каталога из PIM с иерархией и метаданными.
Сохраняет в JSON и опционально создает таблицы в Supabase.
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
OUTPUT_FILE = os.getenv("PIM_CATALOG_OUTPUT", "data/catalog_structure.json")
HTTP_TIMEOUT = float(os.getenv("PIM_HTTP_TIMEOUT", "30"))


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


async def fetch_catalog_tree(client: httpx.AsyncClient) -> list[dict]:
    """Получение полного дерева каталогов."""
    print("📥 Получение дерева каталогов...")
    data = await api_call(client, "GET", "/api/v1/catalog")
    if isinstance(data, list):
        return data
    raise RuntimeError("Неожиданный формат ответа от /api/v1/catalog")


def flatten_catalog_tree(
    tree: list[dict],
    parent_path: list[str] | None = None,
    flat_list: list[dict] | None = None
) -> list[dict]:
    """
    Рекурсивное преобразование дерева каталогов в плоский список.
    
    Сохраняет всю иерархию и метаданные для каждого каталога.
    """
    if flat_list is None:
        flat_list = []
    if parent_path is None:
        parent_path = []

    for catalog in tree:
        current_path = parent_path + [catalog.get("header", "")]
        
        # Извлекаем детей до добавления в список
        children = catalog.pop("children", [])
        
        # Добавляем метаданные для удобной работы
        catalog_entry = {
            "id": catalog.get("id"),
            "header": catalog.get("header"),
            "syncUid": catalog.get("syncUid"),
            "parentId": catalog.get("parentId"),
            "level": catalog.get("level"),
            "lastLevel": catalog.get("lastLevel"),
            "pos": catalog.get("pos"),
            "enabled": catalog.get("enabled", True),
            "deleted": catalog.get("deleted", False),
            "productCount": catalog.get("productCount", 0),
            "productCountAdditional": catalog.get("productCountAdditional", 0),
            "productCountPim": catalog.get("productCountPim", 0),
            "productCountPimAdditional": catalog.get("productCountPimAdditional", 0),
            "lft": catalog.get("lft"),
            "rgt": catalog.get("rgt"),
            "path": " > ".join(current_path),
            "pathArray": current_path.copy(),
            "depth": len(current_path),
            "hasChildren": len(children) > 0,
            "childrenCount": len(children),
            "htHead": catalog.get("htHead"),
            "htDesc": catalog.get("htDesc"),
            "htKeywords": catalog.get("htKeywords"),
            "content": catalog.get("content"),
            "createdAt": catalog.get("createdAt"),
            "updatedAt": catalog.get("updatedAt"),
            "terms": catalog.get("terms", []),
            "picture": catalog.get("picture"),
            "icon": catalog.get("icon"),
            "channels": catalog.get("channels", []),
        }
        
        flat_list.append(catalog_entry)
        
        # Рекурсивная обработка детей
        if children:
            flatten_catalog_tree(children, current_path, flat_list)
    
    return flat_list


def build_hierarchical_map(flat_catalogs: list[dict]) -> dict[int, dict]:
    """
    Создание карты связей родитель -> дети для быстрого доступа.
    """
    hierarchy_map: dict[int, dict] = {}
    
    for catalog in flat_catalogs:
        cat_id = catalog["id"]
        parent_id = catalog["parentId"]
        
        if cat_id not in hierarchy_map:
            hierarchy_map[cat_id] = {
                "catalog": catalog,
                "children_ids": [],
                "parent_id": parent_id
            }
        
        # Добавляем текущий каталог в список детей родителя
        if parent_id and parent_id != cat_id:
            if parent_id not in hierarchy_map:
                hierarchy_map[parent_id] = {
                    "catalog": None,
                    "children_ids": [],
                    "parent_id": None
                }
            hierarchy_map[parent_id]["children_ids"].append(cat_id)
    
    return hierarchy_map


def calculate_statistics(flat_catalogs: list[dict]) -> dict:
    """Расчет статистики по каталогам."""
    total = len(flat_catalogs)
    enabled = sum(1 for c in flat_catalogs if c.get("enabled"))
    deleted = sum(1 for c in flat_catalogs if c.get("deleted"))
    leaf_catalogs = sum(1 for c in flat_catalogs if c.get("lastLevel"))
    with_products = sum(1 for c in flat_catalogs if c.get("productCountPim", 0) > 0)
    
    max_depth = max((c.get("depth", 0) for c in flat_catalogs), default=0)
    total_products = sum(c.get("productCountPim", 0) for c in flat_catalogs)
    
    levels_distribution = {}
    for catalog in flat_catalogs:
        level = catalog.get("level", 0)
        levels_distribution[level] = levels_distribution.get(level, 0) + 1
    
    return {
        "total_catalogs": total,
        "enabled_catalogs": enabled,
        "deleted_catalogs": deleted,
        "leaf_catalogs": leaf_catalogs,
        "catalogs_with_products": with_products,
        "max_depth": max_depth,
        "total_products": total_products,
        "levels_distribution": levels_distribution,
    }


def save_payload(flat_catalogs: list[dict], hierarchy_map: dict[int, dict]) -> None:
    """Сохранение результата в JSON файл."""
    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    
    statistics = calculate_statistics(flat_catalogs)
    
    # Преобразуем hierarchy_map для JSON сериализации
    serializable_hierarchy = {
        str(cat_id): {
            "children_ids": data["children_ids"],
            "parent_id": data["parent_id"]
        }
        for cat_id, data in hierarchy_map.items()
    }
    
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": "COMPO PIM API",
        "statistics": statistics,
        "catalogs": flat_catalogs,
        "hierarchy_map": serializable_hierarchy,
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Структура каталога сохранена в {OUTPUT_FILE}")
    print(f"📊 Статистика:")
    print(f"   • Всего каталогов: {statistics['total_catalogs']}")
    print(f"   • Активных: {statistics['enabled_catalogs']}")
    print(f"   • Удаленных: {statistics['deleted_catalogs']}")
    print(f"   • Конечных (leaf): {statistics['leaf_catalogs']}")
    print(f"   • С товарами: {statistics['catalogs_with_products']}")
    print(f"   • Максимальная глубина: {statistics['max_depth']}")
    print(f"   • Всего товаров: {statistics['total_products']}")
    print(f"   • Распределение по уровням: {statistics['levels_distribution']}")


async def main():
    """Основная функция."""
    ensure_env()
    
    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
        follow_redirects=True,
    ) as client:
        token = await fetch_token(client)
        client.headers["Authorization"] = f"Bearer {token}"
        
        # Получаем полное дерево каталогов
        catalog_tree = await fetch_catalog_tree(client)
        print(f"✅ Получено дерево каталогов")
        
        # Преобразуем в плоский список
        flat_catalogs = flatten_catalog_tree(catalog_tree)
        print(f"✅ Обработано {len(flat_catalogs)} каталогов")
        
        # Строим карту иерархии
        hierarchy_map = build_hierarchical_map(flat_catalogs)
        print(f"✅ Построена карта иерархии")
        
        # Сохраняем результат
        save_payload(flat_catalogs, hierarchy_map)


if __name__ == "__main__":
    asyncio.run(main())

