#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экспорт иерархии групп шаблонов PIM: только ID и названия групп.
Результат: template_groups.json с простым списком групп.

Структура выходного файла:
{
  "generated_at": "ISO 8601 UTC время",
  "group_count": число,
  "groups": [
    {
      "id": ID группы,
      "header": "Название группы",
      "parentId": ID родительской группы (null для корневых)
    }
  ]
}
"""

import asyncio
import json
import os
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("PIM_API_URL", "").rstrip("/")
LOGIN = os.getenv("PIM_LOGIN")
PASSWORD = os.getenv("PIM_PASSWORD")
OUTPUT_FILE = os.getenv("PIM_TEMPLATE_GROUPS_OUTPUT", "data/template_groups.json")
HTTP_TIMEOUT = float(os.getenv("PIM_HTTP_TIMEOUT", 30))


async def api_call(client: httpx.AsyncClient, method: str, path: str, **kwargs):
    resp = await client.request(method, path, **kwargs)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("success") is False:
        raise RuntimeError(data.get("message") or f"Ошибка API {path}")
    return data.get("data", data)


async def fetch_token(client: httpx.AsyncClient) -> str:
    payload = {"login": LOGIN, "password": PASSWORD, "remember": True}
    data = await api_call(client, "POST", "/sign-in/", json=payload)
    token = data.get("access", {}).get("token")
    if not token:
        raise RuntimeError("Авторизация в PIM не удалась")
    return token


async def collect_group_ids_from_templates(client: httpx.AsyncClient) -> set[int]:
    """Собирает уникальные ID групп из полных данных шаблонов."""
    data = await api_call(client, "GET", "/template/autocomplete/20000")
    items = data if isinstance(data, list) else data.get("items") or data.get("templates") or []
    
    if not items:
        return set()
    
    template_ids = [int(item.get("id")) for item in items if item.get("id")]
    print(f"📋 Получаем группы из {len(template_ids)} шаблонов...")
    
    semaphore = asyncio.Semaphore(30)
    group_ids = set()
    
    async def get_group_id(tid: int):
        async with semaphore:
            try:
                tpl = await api_call(client, "GET", f"/template/{tid}")
                gid = tpl.get("templateGroupId")
                if gid:
                    group_ids.add(int(gid))
            except Exception:
                pass
    
    await asyncio.gather(*(get_group_id(tid) for tid in template_ids))
    print(f"📋 Найдено {len(group_ids)} уникальных групп")
    return group_ids


async def fetch_group(client: httpx.AsyncClient, group_id: int) -> dict | None:
    """Получает информацию о группе шаблонов."""
    try:
        data = await api_call(client, "GET", f"/template-group/{group_id}")
        return {
            "id": data.get("id"),
            "header": data.get("header"),
            "parentId": data.get("parentId"),
        }
    except Exception:
        return None


async def fetch_all_groups(client: httpx.AsyncClient, group_ids: set[int]) -> list[dict]:
    """Получает информацию о всех группах и их родителях."""
    semaphore = asyncio.Semaphore(20)
    groups_map: dict[int, dict] = {}
    all_group_ids = set(group_ids)

    async def fetch_one(gid: int):
        async with semaphore:
            group = await fetch_group(client, gid)
            if group:
                groups_map[gid] = group
                parent_id = group.get("parentId")
                if parent_id and parent_id not in all_group_ids:
                    all_group_ids.add(parent_id)

    # Получаем все группы
    await asyncio.gather(*(fetch_one(gid) for gid in group_ids))
    
    # Получаем родительские группы рекурсивно
    missing_parents = all_group_ids - set(groups_map.keys())
    while missing_parents:
        print(f"📋 Получаем {len(missing_parents)} родительских групп...")
        await asyncio.gather(*(fetch_one(gid) for gid in missing_parents))
        missing_parents = all_group_ids - set(groups_map.keys())
    
    results = list(groups_map.values())
    for group in results:
        print(f"✅ {group['header']} (#{group['id']})" + (f" → родитель: {group.get('parentId')}" if group.get('parentId') else ""))
    
    return sorted(results, key=lambda x: x["id"])


def collect_group_ids_from_file() -> set[int] | None:
    """Пытается получить ID групп из существующего файла templates_structure.json."""
    try:
        with open("data/templates_structure.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            group_ids = {t.get("templateGroupId") for t in data.get("templates", []) if t.get("templateGroupId")}
            if group_ids:
                print(f"📋 Найдено {len(group_ids)} групп из файла templates_structure.json")
                return group_ids
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return None


async def main():
    if not BASE_URL or not LOGIN or not PASSWORD:
        raise RuntimeError("Задайте PIM_API_URL, PIM_LOGIN, PIM_PASSWORD в .env")

    # Пробуем сначала получить из файла
    group_ids = collect_group_ids_from_file()
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        token = await fetch_token(client)
        client.headers["Authorization"] = f"Bearer {token}"

        # Если не получили из файла, получаем через API
        if not group_ids:
            group_ids = await collect_group_ids_from_templates(client)
        
        if not group_ids:
            print("❌ Не удалось найти группы шаблонов")
            return
        
        groups = await fetch_all_groups(client, group_ids)

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "group_count": len(groups),
            "groups": groups,
        }

        os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

        print(f"\n💾 Сохранено {len(groups)} групп в {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())

