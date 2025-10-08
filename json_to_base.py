import json
import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

BATCH_SIZE = 250
PARALLEL = 30

async def update_one(session, url, headers, code_1c, guid):
    try:
        async with session.patch(
            f"{url}?code_1c=eq.{code_1c}",
            json={"GUID": guid},
            headers=headers
        ) as resp:
            return resp.status in (200, 204)
    except:
        return False

async def update_batch(session, url, headers, batch, batch_num, total_batches):
    sem = asyncio.Semaphore(PARALLEL)
    
    async def update_with_sem(item):
        async with sem:
            return await update_one(session, url, headers, item["code_1c"], item["GUID"])
    
    tasks = [update_with_sem(item) for item in batch if item.get("code_1c") and item.get("GUID")]
    results = await asyncio.gather(*tasks)
    
    print(f"Батч {batch_num}/{total_batches} | Успешно: {sum(results)}/{len(results)}")

async def main():
    url = f"{os.getenv('SUPABASE_URL')}/rest/v1/products"
    headers = {
        "apikey": os.getenv("SUPABASE_KEY"),
        "Authorization": f"Bearer {os.getenv('SUPABASE_KEY')}",
        "Content-Type": "application/json"
    }
    
    with open("products.json", encoding="utf-8-sig") as f:
        data = json.load(f)
    
    print(f"Всего записей: {len(data)}\n")
    
    batches = [data[i:i + BATCH_SIZE] for i in range(0, len(data), BATCH_SIZE)]
    
    async with aiohttp.ClientSession() as session:
        for i, batch in enumerate(batches, 1):
            await update_batch(session, url, headers, batch, i, len(batches))
    
    print("\nГотово!")

asyncio.run(main())

