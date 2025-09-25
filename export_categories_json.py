#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой скрипт для экспорта категорий из Supabase в JSON
"""

import os
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Конфигурация
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def main():
    try:
        print("🗄️ Подключаемся к Supabase...")
        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        print("📋 Получаем все категории...")
        response = client.table("categories").select("*").order("level,id").execute()

        if response.data:
            print(f"✅ Получено {len(response.data)} категорий")

            # Сохраняем в JSON с красивым форматированием
            output_file = "categories_export.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(response.data, f, ensure_ascii=False, indent=2, default=str)

            print(f"💾 Данные сохранены в файл: {output_file}")
            print(f"📊 Структура: {len(response.data)} категорий")

            # Показываем статистику по уровням
            levels = {}
            for category in response.data:
                level = category["level"]
                levels[level] = levels.get(level, 0) + 1

            print("📈 Распределение по уровням:")
            for level in sorted(levels.keys()):
                print(f"   Level {level}: {levels[level]} категорий")

        else:
            print("❌ Категории не найдены в таблице")

    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    main()
