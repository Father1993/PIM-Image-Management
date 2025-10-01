#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для обновления image_url в Supabase актуальными ссылками из PIM API
Расширения файлов в uppercase (.PNG, .JPG и т.д.)
"""
import os
import re
import asyncio
import requests
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PIM_API_URL = os.getenv("PIM_API_URL")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")
PIM_IMAGE_URL = os.getenv("PIM_IMAGE_URL")


def uppercase_extension(url):
    """Преобразует расширение файла в URL в uppercase"""
    if not url:
        return url

    pattern = r"\.(jpg|jpeg|png|gif|bmp|webp|svg)(\?|$|#)"

    def replacer(match):
        ext = match.group(1).upper()
        rest = match.group(2)
        return f".{ext}{rest}"

    return re.sub(pattern, replacer, url, flags=re.IGNORECASE)


class ImageUrlUpdater:
    def __init__(self):
        self.token = None
        self.base_url = PIM_API_URL
        self.headers = {"Content-Type": "application/json"}
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.table_name = None

    def authenticate(self):
        """Получение токена авторизации PIM API"""
        auth_data = {"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
        response = requests.post(
            f"{self.base_url}/sign-in/", json=auth_data, headers=self.headers
        )
        response.raise_for_status()
        self.token = response.json()["data"]["access"]["token"]
        self.headers["Authorization"] = f"Bearer {self.token}"

    def find_supabase_table(self):
        """Определение названия таблицы в Supabase"""
        table_names = ["product", "products", "Product", "Products"]
        for table_name in table_names:
            try:
                self.supabase.table(table_name).select("id").limit(1).execute()
                self.table_name = table_name
                print(f"Найдена таблица: {table_name}")
                return True
            except:
                continue
        return False

    async def get_all_products_from_pim(self):
        """Получение всех товаров с изображениями из PIM через scroll API"""
        scroll_id = None
        products_with_images = []
        batch_num = 0

        while True:
            batch_num += 1
            url = f"{self.base_url}/product/scroll"
            if scroll_id:
                url += f"?scrollId={scroll_id}"

            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            response_data = response.json()

            if not response_data.get("success", False):
                print(f"❌ API вернул ошибку: {response_data.get('message')}")
                break

            data = response_data.get("data", {})
            current_batch = data.get("productElasticDtos", [])

            if not current_batch:
                print("⛔ Нет товаров в пакете, завершаем...")
                break

            # Извлекаем товары с изображениями
            for product in current_batch:
                picture = product.get("picture")
                if picture:
                    image_url = f"{PIM_IMAGE_URL}/{picture}"
                    image_url = uppercase_extension(image_url)
                    products_with_images.append(
                        {"id": product.get("id"), "image_url": image_url}
                    )

            print(
                f"Пакет {batch_num}: обработано {len(current_batch)} товаров, найдено с изображениями: {len(products_with_images)}"
            )

            scroll_id = data.get("scrollId")
            if not scroll_id:
                print("⛔ Нет scrollId, завершаем...")
                break

        return products_with_images

    async def update_supabase_batch(self, products_batch):
        """Обновление пакета товаров в Supabase"""
        updated = 0
        for product in products_batch:
            try:
                self.supabase.table(self.table_name).update(
                    {"image_url": product["image_url"]}
                ).eq("id", product["id"]).execute()
                updated += 1
            except Exception as e:
                print(f"Ошибка обновления товара {product['id']}: {e}")
        return updated

    async def update_all_products(self, products):
        """Обновление всех товаров в Supabase пакетами"""
        total_updated = 0
        batch_size = 100

        for i in range(0, len(products), batch_size):
            batch = products[i : i + batch_size]
            updated = await self.update_supabase_batch(batch)
            total_updated += updated
            print(f"Обновлено {total_updated}/{len(products)} товаров")

        return total_updated


async def main():
    updater = ImageUrlUpdater()

    try:
        print("🔐 Авторизация в PIM API...")
        updater.authenticate()
        print("✅ Авторизация успешна")

        print("🔍 Поиск таблицы в Supabase...")
        if not updater.find_supabase_table():
            print("❌ Таблица не найдена в Supabase!")
            return

        print("📦 Получение товаров с изображениями из PIM API...")
        products = await updater.get_all_products_from_pim()
        print(f"✅ Получено {len(products)} товаров с изображениями")

        if not products:
            print("⚠️ Нет товаров для обновления")
            return

        print("💾 Обновление URL изображений в Supabase...")
        total_updated = await updater.update_all_products(products)
        print(f"✅ Готово! Обновлено {total_updated} товаров")

    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
