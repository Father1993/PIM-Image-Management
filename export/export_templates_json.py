#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экспорт шаблонов из PIM в JSON
"""

import os
import json
import asyncio
import httpx
import requests
from dotenv import load_dotenv

load_dotenv()

PIM_API_URL = os.getenv("PIM_API_URL")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")


def authenticate():
    """Авторизация в PIM API через requests (проверенный способ)"""
    base_url = PIM_API_URL.rstrip('/')
    # Пробуем оба варианта URL
    for url in [f"{base_url}/sign-in/", f"{base_url}/api/v1/sign-in/"]:
        try:
            response = requests.post(
                url,
                json={"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
            )
            if response.status_code == 200:
                return response.json()["data"]["access"]["token"]
        except Exception:
            continue
    raise Exception("Не удалось авторизоваться")


async def get_template(client, token, template_id, semaphore):
    """Получение шаблона по ID"""
    async with semaphore:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            url = f"{PIM_API_URL.rstrip('/')}/template/{template_id}"
            response = await client.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return template_id, data.get("data") if data.get("success") else None
        except Exception as e:
            print(f"  ⚠️ Ошибка для ID={template_id}: {e}")
        return template_id, None


def _save_templates_sync(templates, output_file):
    """Синхронное сохранение шаблонов в файл"""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=2, default=str)


async def save_templates_async(templates, output_file="templates_export.json"):
    """Асинхронное сохранение шаблонов в файл (не блокирует основной поток)"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _save_templates_sync, templates.copy(), output_file)


async def main():
    print("🔐 Авторизация в PIM API...")
    token = authenticate()
    print("✅ Авторизация успешна\n")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        print("📋 Загружаем ID из ID-temp.json...")
        with open("ID-temp.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        template_ids = [item["id"] for item in (data if isinstance(data, list) else data.get("data", [data]))]
        total = len(template_ids)
        print(f"✅ Найдено {total} шаблонов\n")

        print("📥 Получаем данные шаблонов (параллельно через httpx)...")
        semaphore = asyncio.Semaphore(250)  
        templates = []
        output_file = "templates_export.json"
        completed = 0

        # Создаем все задачи сразу - они будут выполняться параллельно
        tasks = [asyncio.create_task(get_template(client, token, tid, semaphore)) for tid in template_ids]
        processed_ids = set()
        
        try:
            for coro in asyncio.as_completed(tasks):
                try:
                    template_id, template = await coro
                    completed += 1
                    processed_ids.add(template_id)
                    
                    if template:
                        templates.append(template)
                        print(f"✅ [{completed}/{total}] ID={template_id}")
                    else:
                        print(f"❌ [{completed}/{total}] ID={template_id} - не найден")
                    
                    # Асинхронно сохраняем каждые 500 шаблонов (не блокирует обработку)
                    if completed % 500 == 0:
                        asyncio.create_task(save_templates_async(templates, output_file))
                        print(f"💾 Асинхронное сохранение: {len(templates)} шаблонов")
                except asyncio.CancelledError:
                    break

        except KeyboardInterrupt:
            print(f"\n⚠️ Прерывание! Сохраняем данные...")
        finally:
            # Отменяем все оставшиеся задачи
            for task in tasks:
                if not task.done():
                    task.cancel()
            # Собираем все завершенные задачи, которые еще не обработаны
            for task in tasks:
                if task.done() and not task.cancelled():
                    try:
                        template_id, template = task.result()
                        if template_id not in processed_ids:
                            processed_ids.add(template_id)
                            if template:
                                templates.append(template)
                    except Exception:
                        pass
            
            # Сохраняем данные (синхронно в finally, чтобы гарантировать сохранение)
            _save_templates_sync(templates, output_file)
            print(f"💾 Данные сохранены в файл: {output_file}")
            print(f"📊 Сохранено {len(templates)} из {total} шаблонов")
            
            if completed < total:
                return

        # Финальное сохранение
        await save_templates_async(templates, output_file)
        print(f"\n💾 Данные сохранены в файл: {output_file}")
        print(f"📊 Экспортировано {len(templates)} из {total} шаблонов")


if __name__ == "__main__":
    asyncio.run(main())

