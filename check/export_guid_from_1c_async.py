#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Асинхронный экспорт guid из файла 1С в таблицу Supabase new_onec_products.
Ищем товар по code_1c (в JSON это поле "Code") и записываем guid в guid_1c.
"""

import asyncio
import json
import os
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "1c_catalog_to_pim.JSON"

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE = os.getenv("SUPABASE_PRODUCTS_TABLE", "new_onec_products")
PAGE_SIZE = int(os.getenv("GUID_PAGE_SIZE", "1000"))
CONCURRENCY = int(os.getenv("GUID_CONCURRENCY", "25"))

REST_URL = f"{SUPABASE_URL}/rest/v1/{TABLE}" if SUPABASE_URL else ""


def require_settings() -> None:
    missing = [
        name
        for name, value in (
            ("SUPABASE_URL", SUPABASE_URL),
            ("SUPABASE_KEY", SUPABASE_KEY),
        )
        if not value
    ]
    if missing:
        raise SystemExit(f"❌ Заполните переменные окружения: {', '.join(missing)}")
    if not DATA_FILE.exists():
        raise SystemExit(f"❌ Не найден файл с каталогом: {DATA_FILE}")


def load_guid_map(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8-sig") as src:
        raw = json.load(src)
    return {
        item.get("Code"): item.get("guid")
        for item in raw
        if item.get("Code") and item.get("guid")
    }


def build_headers(prefer: str | None = None) -> dict[str, str]:
    headers = {
        "apikey": SUPABASE_KEY or "",
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Accept": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


async def fetch_supabase_rows(session: aiohttp.ClientSession) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    headers = build_headers()

    while True:
        params = {
            "select": "id,code_1c,guid_1c",
            "guid_1c": "is.null",
            "limit": PAGE_SIZE,
            "offset": offset,
            "order": "code_1c",
        }
        async with session.get(REST_URL, params=params, headers=headers) as resp:
            if resp.status == 416:
                break
            if resp.status not in (200, 206):
                detail = await resp.text()
                raise RuntimeError(
                    f"Ошибка чтения Supabase ({resp.status}): {detail or 'нет тела'}"
                )
            chunk = await resp.json()

        if not chunk or len(chunk) < PAGE_SIZE:
            if chunk:
                rows.extend(chunk)
            break

        rows.extend(chunk)
        offset += PAGE_SIZE

    return rows


async def patch_guid(
    session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, code: str, guid: str
) -> bool:
    params = {"code_1c": f"eq.{code}"}
    payload = {"guid_1c": guid}
    headers = {**build_headers(), "Content-Type": "application/json", "Prefer": "return=minimal"}

    async with semaphore:
        try:
            async with session.patch(
                REST_URL,
                params=params,
                json=payload,
                headers=headers,
            ) as resp:
                if resp.status in (200, 204):
                    return True
                detail = await resp.text()
                print(f"❌ Не удалось обновить {code}: {resp.status} {detail}")
        except aiohttp.ClientError as error:
            print(f"❌ Сеть: {code}: {error}")
    return False


async def main() -> None:
    require_settings()
    guid_map = load_guid_map(DATA_FILE)
    if not guid_map:
        raise SystemExit("❌ В файле 1С нет записей с guid")

    print(f"📊 В файле 1С найдено {len(guid_map)} записей с guid")

    timeout = aiohttp.ClientTimeout(total=None)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        supabase_rows = await fetch_supabase_rows(session)
        print(f"📥 Найдено {len(supabase_rows)} записей в Supabase без guid_1c")

        pairs: list[tuple[str, str]] = []
        missing_codes = []
        for row in supabase_rows:
            code = (row or {}).get("code_1c")
            if not code:
                continue
            guid = guid_map.get(code)
            if guid:
                pairs.append((code, guid))
            else:
                missing_codes.append(code)

        missing = len(supabase_rows) - len(pairs)
        if missing:
            print(f"⚠️ Пропущено {missing} записей (нет guid в файле 1С для этих code_1c)")
            if missing_codes[:5]:
                print(f"   Примеры code_1c без guid: {', '.join(missing_codes[:5])}")

        if not pairs:
            print("✅ Обновлять нечего")
            return

        print(f"🚀 Обновляем {len(pairs)} товаров (потоков: {CONCURRENCY})")
        semaphore = asyncio.Semaphore(CONCURRENCY)
        tasks = [patch_guid(session, semaphore, code, guid) for code, guid in pairs]

        updated = errors = 0
        for idx, coro in enumerate(asyncio.as_completed(tasks), 1):
            if await coro:
                updated += 1
            else:
                errors += 1
            if idx % 100 == 0 or idx == len(pairs):
                print(f"➡️  Готово {idx}/{len(pairs)} | ok: {updated} | errors: {errors}")

        print(f"🏁 Итог: обновлено {updated}, ошибок {errors}")


if __name__ == "__main__":
    asyncio.run(main())

