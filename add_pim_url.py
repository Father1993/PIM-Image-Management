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


async def main():
    # Подключение к Supabase
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Загрузка Excel файла
    df = pd.read_excel("no-size.xlsx")
    print(f"Загружено {len(df)} товаров")

    # Получение всех product_id из файла (только числовые значения)
    product_ids = (
        df[pd.to_numeric(df["ID товара"], errors="coerce").notna()]["ID товара"]
        .astype(int)
        .tolist()
    )

    # Попробуем разные названия таблиц
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

    # Получение ссылок порциями (по 100 ID)
    links_dict = {}
    for i in range(0, len(product_ids), 100):
        batch = product_ids[i : i + 100]
        response = (
            client.table(table_found).select("id, link_pim").in_("id", batch).execute()
        )
        links_dict.update({item["id"]: item["link_pim"] for item in response.data})
        print(f"Обработано {min(i+100, len(product_ids))}/{len(product_ids)} товаров")

    # Добавление колонки со ссылками
    df["Ссылка на товар"] = df["ID товара"].map(links_dict)

    # Получение недостающих ссылок через PIM API (только числовые ID)
    numeric_mask = pd.to_numeric(df["ID товара"], errors="coerce").notna()
    missing_mask = df["Ссылка на товар"].isna() & numeric_mask
    missing_ids = df[missing_mask]["ID товара"].astype(int).tolist()

    if missing_ids:
        print(
            f"Получаем недостающие ссылки для {len(missing_ids)} товаров через PIM API..."
        )

        async with aiohttp.ClientSession() as session:
            # Получаем токен авторизации
            token = await get_pim_token(session)
            if not token:
                print("Не удалось получить токен авторизации PIM API")
                return

            # Получаем ссылки для товаров
            tasks = [
                get_pim_product(session, product_id, token)
                for product_id in missing_ids
            ]
            pim_links = await asyncio.gather(*tasks)

        # Обновляем DataFrame недостающими ссылками
        pim_links_dict = {
            missing_ids[i]: link for i, link in enumerate(pim_links) if link
        }
        df.loc[df["ID товара"].isin(pim_links_dict.keys()), "Ссылка на товар"] = df.loc[
            df["ID товара"].isin(pim_links_dict.keys()), "ID товара"
        ].map(pim_links_dict)

        print(f"Получено {len(pim_links_dict)} дополнительных ссылок из PIM API")

    # Сохранение обновленного файла
    output_file = "no-size-updated.xlsx"
    df.to_excel(output_file, index=False)
    total_links = len([x for x in df["Ссылка на товар"] if x])
    print(f"Итого добавлено {total_links} ссылок")
    print(f"Результат сохранен в {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
