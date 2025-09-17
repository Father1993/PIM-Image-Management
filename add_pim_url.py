import os
import asyncio
import pandas as pd
import aiohttp
import base64
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()


PIM_API_URL = os.getenv("PIM_API_URL")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


async def get_pim_token(session):
    """Получить токен авторизации PIM API"""
    login_data = {"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}

    try:
        async with session.post(f"{PIM_API_URL}/sign-in/", json=login_data) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("success") and data.get("data", {}).get("access", {}).get(
                    "token"
                ):
                    return data["data"]["access"]["token"]
    except Exception as e:
        print(f"Ошибка получения токена: {e}")
    return None


async def get_pim_product(session, product_id, token):
    """Получить данные товара из PIM API"""
    headers = {"Authorization": f"Bearer {token}"}

    try:
        url = f"{PIM_API_URL}/product/{product_id}"
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("success") and data.get("data"):
                    catalog_id = data["data"]["catalog"]["id"]
                    return f"https://pim.uroven.pro/cabinet/pim/catalog/{catalog_id}/products/item/edit/{product_id}"
    except Exception as e:
        print(f"Ошибка получения товара {product_id}: {e}")
    return None


async def update_supabase_products(client, table_name, products_with_links):
    """Обновить товары в Supabase с полученными ссылками"""
    updated_count = 0

    # Обновляем пакетами по 100 товаров
    for i in range(0, len(products_with_links), 100):
        batch = products_with_links[i : i + 100]

        # Создаем асинхронные задачи для параллельного обновления
        async def update_product(product):
            try:
                client.table(table_name).update({"link_pim": product["link"]}).eq(
                    "id", product["id"]
                ).execute()
                return True
            except Exception as e:
                print(f"Ошибка обновления товара {product['id']}: {e}")
                return False

        # Выполняем обновления параллельно (по 20 штук чтобы не перегружать сервер)
        tasks = []
        for j in range(0, len(batch), 20):
            mini_batch = batch[j : j + 20]
            mini_tasks = [update_product(product) for product in mini_batch]
            mini_results = await asyncio.gather(*mini_tasks, return_exceptions=True)
            updated_count += sum(1 for result in mini_results if result is True)

        print(
            f"Обновлено {min(i+100, updated_count)}/{len(products_with_links)} товаров"
        )

    return updated_count


async def main():
    # Подключение к Supabase
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Определяем название таблицы
    table_names = ["product", "products", "Product", "Products"]
    table_found = None

    for table_name in table_names:
        try:
            test = client.table(table_name).select("id").limit(1).execute()
            table_found = table_name
            print(f"Найдена таблица: {table_name}")
            break
        except:
            continue

    if not table_found:
        print("Таблица не найдена! Проверьте название таблицы в Supabase")
        return

    # Получаем товары без link_pim
    print("Получаем товары без ссылок из Supabase...")
    response = client.table(table_found).select("id").is_("link_pim", "null").execute()

    if not response.data:
        print("Все товары в Supabase уже имеют ссылки!")
        return

    # Получаем ID товаров без ссылок
    missing_ids = [item["id"] for item in response.data]
    print(f"Найдено {len(missing_ids)} товаров без ссылок в Supabase")

    # Сохраняем ID товаров в файл для архива
    with open("products_without_links.txt", "w") as f:
        f.write("\n".join(map(str, missing_ids)))
    print(f"Список ID товаров сохранен в products_without_links.txt")

    # Получаем ссылки через PIM API
    if missing_ids:
        print(f"Получаем ссылки для {len(missing_ids)} товаров через PIM API...")

        async with aiohttp.ClientSession() as session:
            # Получаем токен авторизации
            token = await get_pim_token(session)
            if not token:
                print("Не удалось получить токен авторизации PIM API")
                return

            # Получаем ссылки для товаров с ограничением одновременных запросов
            # Используем пакетную обработку для снижения нагрузки
            pim_links = []
            for i in range(0, len(missing_ids), 50):
                batch = missing_ids[i : i + 50]
                batch_tasks = [
                    get_pim_product(session, product_id, token) for product_id in batch
                ]
                batch_results = await asyncio.gather(*batch_tasks)
                pim_links.extend(batch_results)
                print(
                    f"Получены ссылки для {i+len(batch)} из {len(missing_ids)} товаров"
                )

        # Формируем список товаров с полученными ссылками
        products_with_links = [
            {"id": missing_ids[i], "link": link}
            for i, link in enumerate(pim_links)
            if link
        ]

        print(f"Получено {len(products_with_links)} ссылок из PIM API")

        # Обновляем товары в Supabase
        if products_with_links:
            updated_count = await update_supabase_products(
                client, table_found, products_with_links
            )
            print(f"Итого обновлено {updated_count} товаров в Supabase")

            # Проверяем оставшиеся товары без ссылок
            remaining = len(missing_ids) - updated_count
            if remaining > 0:
                print(f"Осталось {remaining} товаров без ссылок")
        else:
            print("Не удалось получить ссылки через PIM API")


if __name__ == "__main__":
    asyncio.run(main())
