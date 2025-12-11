#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Экспорт иерархии шаблонов PIM: шаблон -> группы -> характеристики -> значения.
Результат: templates_structure.json с плоским, легко переносимым описанием.

Структура выходного файла:
{
  "generated_at": "ISO 8601 UTC время",
  "template_count": число,
  "templates": [
    {
      "id": ID шаблона,
      "header": "Название",
      "groups": [
        {
          "id": ID группы,
          "header": "Название группы",
          "features": [
            {
              "id": ID характеристики,
              "featureId": ID базовой характеристики,
              "header": "Название",
              "type": {"code": "string|range|select|boolean", ...},
              "values": [{"id": ..., "value": "..."}]  # только для select
            }
          ]
        }
      ]
    }
  ]
}

Подробная документация: data/templates_structure.README.md
"""

import asyncio
import json
import os
from datetime import datetime

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("PIM_API_URL", "").rstrip("/")
LOGIN = os.getenv("PIM_LOGIN")
PASSWORD = os.getenv("PIM_PASSWORD")
OUTPUT_FILE = os.getenv("PIM_TEMPLATE_OUTPUT", "data/templates_structure.json")
TEMPLATE_LIMIT = int(os.getenv("PIM_TEMPLATE_LIMIT", "20000"))
HTTP_TIMEOUT = float(os.getenv("PIM_HTTP_TIMEOUT", 30))
HTTP_LIMITS = httpx.Limits(max_connections=40, max_keepalive_connections=20)


def ensure_env() -> None:
    if not BASE_URL or not LOGIN or not PASSWORD:
        raise RuntimeError("Задайте PIM_API_URL, PIM_LOGIN, PIM_PASSWORD в .env")


async def api_call(client: httpx.AsyncClient, method: str, path: str, **kwargs):
    resp = await client.request(method, path, **kwargs)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("success") is False:
        raise RuntimeError(data.get("message") or f"Ошибка API {path}")
    return data.get("data", data)


async def fetch_token(client: httpx.AsyncClient) -> str:
    payload = {"login": LOGIN, "password": PASSWORD, "remember": True}
    try:
        data = await api_call(client, "POST", "/sign-in/", json=payload)
        token = data.get("access", {}).get("token")
        if token:
            return token
    except httpx.HTTPError:
        pass
    raise RuntimeError("Авторизация в PIM не удалась")


async def fetch_template_ids(client: httpx.AsyncClient) -> list[int]:
    data = await api_call(client, "GET", f"/template/autocomplete/{TEMPLATE_LIMIT}")
    raw_items = data if isinstance(data, list) else data.get("items") or data.get("templates") or []
    ids = sorted({int(item.get("id")) for item in raw_items if item.get("id")})
    if not ids:
        raise RuntimeError("PIM не вернул список шаблонов")
    print(f"📋 Найдено {len(ids)} шаблонов для выгрузки")
    return ids


async def fetch_templates(client: httpx.AsyncClient, template_ids: list[int]) -> list[dict]:
    semaphore = asyncio.Semaphore(50)
    results: list[dict] = []

    async def fetch_one(tid: int):
        async with semaphore:
            try:
                data = await api_call(client, "GET", f"/template/{tid}")
                print(f"✅ Шаблон {tid} загружен")
                return data
            except Exception as exc:  # noqa: BLE001
                print(f"❌ Не удалось загрузить шаблон {tid}: {exc}")
                return None

    tasks = [asyncio.create_task(fetch_one(tid)) for tid in template_ids]
    for coro in asyncio.as_completed(tasks):
        tpl = await coro
        if tpl:
            results.append(tpl)
    return results


def collect_feature_value_ids(templates: list[dict]) -> set[int]:
    value_ids: set[int] = set()
    for template in templates:
        for group in template.get("groups") or []:
            for feature in group.get("features") or []:
                for raw_value in feature.get("featureValues") or []:
                    if isinstance(raw_value, dict):
                        vid = raw_value.get("id")
                    else:
                        vid = raw_value
                    if isinstance(vid, int):
                        value_ids.add(vid)
    return value_ids


async def fetch_feature_values(client: httpx.AsyncClient, value_ids: set[int]) -> dict[int, dict]:
    if not value_ids:
        return {}
    semaphore = asyncio.Semaphore(100)
    cache: dict[int, dict] = {}

    async def fetch_one(value_id: int):
        async with semaphore:
            try:
                data = await api_call(client, "GET", f"/feature-value/{value_id}")
                cache[value_id] = {
                    "id": data.get("id"),
                    "value": data.get("value") or data.get("header"),
                    "code": data.get("code"),
                    "color": data.get("color"),
                    "hash": data.get("hash"),
                    "enabled": data.get("enabled"),
                    "deleted": data.get("deleted"),
                }
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️ Не удалось получить значение характеристики {value_id}: {exc}")

    await asyncio.gather(*(fetch_one(vid) for vid in value_ids))
    print(f"🔢 Загружено {len(cache)}/{len(value_ids)} значений характеристик")
    return cache


def simplify_templates(templates: list[dict], value_map: dict[int, dict]) -> dict:
    simplified: list[dict] = []
    for tpl in templates:
        groups_out: list[dict] = []
        for group in tpl.get("groups") or []:
            features_out: list[dict] = []
            for feature in group.get("features") or []:
                values = []
                for raw_value in feature.get("featureValues") or []:
                    vid = raw_value.get("id") if isinstance(raw_value, dict) else raw_value
                    if isinstance(vid, int):
                        values.append(value_map.get(vid) or {"id": vid, "value": None})
                features_out.append(
                    {
                        "id": feature.get("id"),
                        "featureId": feature.get("featureId"),
                        "header": feature.get("header"),
                        "type": {
                            "id": feature.get("featureTypeId"),
                            "code": feature.get("featureTypeCode"),
                            "name": feature.get("featureTypeHeader"),
                        },
                        "required": feature.get("required"),
                        "multiple": feature.get("multiple"),
                        "isFilter": feature.get("isFilter"),
                        "keyFeature": feature.get("keyFeature"),
                        "units": feature.get("units") or [],
                        "validatorId": feature.get("validatorId"),
                        "sort": feature.get("sort"),
                        "featureGroupId": feature.get("featureGroupId"),
                        "values": values,
                    }
                )
            groups_out.append(
                {
                    "id": group.get("id"),
                    "header": group.get("header"),
                    "groupId": group.get("groupId"),
                    "templateId": group.get("templateId"),
                    "sort": group.get("sort"),
                    "features": features_out,
                }
            )
        simplified.append(
            {
                "id": tpl.get("id"),
                "header": tpl.get("header"),
                "templateGroupId": tpl.get("templateGroupId"),
                "templateGroupTree": tpl.get("templateGroupTree") or [],
                "cases": tpl.get("cases"),
                "syncUid": tpl.get("syncUid"),
                "featureCount": tpl.get("featureCount"),
                "keyFeatureCount": tpl.get("keyFeatureCount"),
                "productCount": tpl.get("productCount"),
                "enabled": tpl.get("enabled"),
                "deleted": tpl.get("deleted"),
                "groups": groups_out,
            }
        )
    simplified.sort(key=lambda item: item["id"])
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "template_count": len(simplified),
        "templates": simplified,
    }


def save_payload(payload: dict) -> None:
    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"💾 Структура сохранена в {OUTPUT_FILE}")


async def main():
    ensure_env()
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=HTTP_TIMEOUT,
        limits=HTTP_LIMITS,
        follow_redirects=True,
    ) as client:
        token = await fetch_token(client)
        client.headers["Authorization"] = f"Bearer {token}"
        template_ids = await fetch_template_ids(client)
        templates_raw = await fetch_templates(client, template_ids)
        value_ids = collect_feature_value_ids(templates_raw)
        value_map = await fetch_feature_values(client, value_ids)
        payload = simplify_templates(templates_raw, value_map)
        save_payload(payload)


if __name__ == "__main__":
    asyncio.run(main())

