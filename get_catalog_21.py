#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Асинхронный скрипт для загрузки каталога категорий из Compo PIM в Supabase
"""

import os
import asyncio
import aiohttp
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Конфигурация
PIM_API_URL = os.getenv("PIM_API_URL")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


class CatalogSyncer:
    def __init__(self):
        self.token = None
        self.categories = []

    async def authenticate(self, session):
        """Авторизация в PIM API"""
        auth_data = {"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}

        async with session.post(f"{PIM_API_URL}/sign-in/", json=auth_data) as response:
            response.raise_for_status()
            data = await response.json()
            self.token = data["data"]["access"]["token"]
            return self.token

    async def get_catalog(self, session):
        """Получение каталога с ID-21"""
        headers = {"Authorization": f"Bearer {self.token}"}

        async with session.get(
            f"{PIM_API_URL}/catalog/21", headers=headers
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return data["data"]

    def parse_categories(self, category, parent_id=None, level=0):
        """Рекурсивный обход дерева категорий"""
        # Добавляем текущую категорию
        self.categories.append(
            {
                "id": category["id"],
                "parent_id": parent_id,
                "header": category["header"],
                "sync_uid": category["syncUid"],
                "level": category.get(
                    "level", level
                ),  # Используем level из API если есть
                "product_count": category.get("productCount", 0),
                "product_count_additional": category.get("productCountAdditional", 0),
                "created_at": category.get("createdAt"),
                "updated_at": category.get("updatedAt"),
            }
        )

        # Обрабатываем вложенные категории
        for child in category.get("children", []):
            self.parse_categories(
                child, category["id"], category.get("level", level) + 1
            )

    def clear_and_insert(self, client):
        """Очистка таблицы и вставка новых данных"""
        try:
            # Очищаем таблицу
            client.table("categories").delete().neq("id", 0).execute()
            print(f"🗑️ Таблица categories очищена")

            # Вставляем категории пакетами по 100
            for i in range(0, len(self.categories), 100):
                batch = self.categories[i : i + 100]
                client.table("categories").insert(batch).execute()
                print(
                    f"📝 Вставлено {min(i+100, len(self.categories))}/{len(self.categories)} категорий"
                )
        except Exception as e:
            if "does not exist" in str(e):
                print(
                    "❌ Таблица categories не существует! Создайте её в Supabase SQL Editor"
                )
            raise


async def main():
    try:
        print("🚀 Начинаем синхронизацию каталога...")

        syncer = CatalogSyncer()

        # Работаем с PIM API
        async with aiohttp.ClientSession() as session:
            print("🔐 Авторизация в PIM API...")
            await syncer.authenticate(session)
            print("✅ Авторизация успешна")

            print("📂 Загружаем каталог ID-21...")
            catalog_data = await syncer.get_catalog(session)
            print("✅ Каталог загружен")

            print("🔄 Обрабатываем дерево категорий...")
            # Сначала добавляем корневую категорию (id=21)
            syncer.parse_categories(catalog_data, catalog_data.get("parentId"))
            print(f"✅ Обработано {len(syncer.categories)} категорий")

        # Работаем с Supabase
        print("🗄️ Подключаемся к Supabase...")
        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        print("💾 Сохраняем категории в базу данных...")
        syncer.clear_and_insert(client)

        print(
            f"🎉 Синхронизация завершена! Загружено {len(syncer.categories)} категорий"
        )

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
