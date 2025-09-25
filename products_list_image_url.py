import os
import json
import asyncio
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


async def main():
    try:
        # Подключение к Supabase
        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        print("Подключение к базе данных установлено")

        # Получаем данные из таблицы products
        response = client.table("products").select("code_1c, image_url").execute()

        if response.data:
            print(f"Получено записей: {len(response.data)}")

            # Подготавливаем данные для JSON
            products_data = []
            for product in response.data:
                product_info = {
                    "code_1c": product.get("code_1c"),
                    "image_url": product.get("image_url"),
                }
                products_data.append(product_info)

            # Сохраняем в JSON файл
            output_filename = "products_images.json"
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(products_data, f, ensure_ascii=False, indent=2)

            print(f"Данные сохранены в файл: {output_filename}")
            print(f"Всего записей в JSON: {len(products_data)}")

        else:
            print("Данные не найдены в таблице products")

    except Exception as e:
        print(f"Ошибка при выполнении скрипта: {e}")


if __name__ == "__main__":
    asyncio.run(main())
