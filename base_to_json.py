import json
import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

async def main():
    url = f"{os.getenv('SUPABASE_URL')}/rest/v1/products"
    headers = {
        "apikey": os.getenv("SUPABASE_KEY"),
        "Authorization": f"Bearer {os.getenv('SUPABASE_KEY')}"
    }
    
    all_data = []
    last_id = 0
    limit = 1000
    
    async with aiohttp.ClientSession() as session:
        while True:
            params = {
                "select": "id,code_1c,GUID,image_optimized_url",
                "id": f"gt.{last_id}",
                "limit": limit,
                "order": "id.asc"
            }
            
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    print(f"Ошибка: {resp.status}")
                    break
                chunk = await resp.json()
                if not chunk:
                    break
                
                all_data.extend(chunk)
                last_id = chunk[-1]["id"]
                print(f"Загружено: {len(all_data)}")
    
    # Фильтруем только с GUID и удаляем дубли
    unique = {}
    for item in all_data:
        if item.get("GUID"):
            unique[item["GUID"]] = {
                "code_1c": item.get("code_1c"),
                "GUID": item["GUID"],
                "image_optimized_url": item.get("image_optimized_url")
            }
    
    data = list(unique.values())
    print(f"\nВсего: {len(all_data)} | С GUID: {len(data)}")
    
    with open("export.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("Данные сохранены в export.json")

asyncio.run(main())
