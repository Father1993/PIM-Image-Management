#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для загрузки данных о поставщиках из JSON файла в таблицу Supabase vendors_products
"""

import os
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def prepare_data(data):
    """Подготавливает данные для загрузки в базу (минимальные изменения типов)"""
    for item in data:
        # Преобразуем inn из числа в строку (в базе text)
        if "inn" in item and item["inn"] is not None:
            item["inn"] = str(item["inn"])
        
        # Убираем id, если есть (база сгенерирует сама)
        item.pop("id", None)
    
    return data


def main():
    json_file = "uroven_vendors.json"
    table_name = "uroven_vendors"
    
    try:
        # Подключение к Supabase
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Подключение к базе данных установлено")
        # Проверка существования таблицы (попытка прочитать одну запись)
        try:
            test_response = client.table(table_name).select("*").limit(1).execute()
            print(f"✅ Таблица '{table_name}' найдена")
        except Exception as e:
            print(f"❌ Таблица '{table_name}' не найдена или нет доступа")
            print(f"Ошибка: {e}")
            return

        # Загрузка данных из JSON
        with open(json_file, "r", encoding="utf-8") as f:
            vendors_data = json.load(f)

        print(f"📂 Загружено {len(vendors_data)} записей из {json_file}")

        # Подготовка данных: преобразование типов для совместимости с базой
        vendors_data = prepare_data(vendors_data)
        print(f"✅ Данные подготовлены (inn -> text)")

        # Пробуем вставить первую запись для проверки
        skip_first = False
        if vendors_data:
            print("🔍 Проверка первой записи...")
            try:
                test_record = [vendors_data[0].copy()]
                test_response = client.table(table_name).insert(test_record).execute()
                print("✅ Тестовая запись успешно вставлена")
                skip_first = True  # Пропускаем первую запись в основном цикле
                total_inserted = 1
            except Exception as test_error:
                print(f"❌ Ошибка при вставке тестовой записи:")
                print(f"Данные: {json.dumps(test_record[0], ensure_ascii=False, indent=2)}")
                print(f"Ошибка: {test_error}")
                return

        # Вставка данных пакетами по 100 записей
        batch_size = 100
        if not skip_first:
            total_inserted = 0
        start_index = 1 if skip_first else 0

        for i in range(start_index, len(vendors_data), batch_size):
            batch = vendors_data[i : i + batch_size]
            try:
                response = client.table(table_name).insert(batch).execute()
                inserted_count = len(response.data) if response.data else 0
                total_inserted += inserted_count
                print(
                    f"📝 Вставлено {total_inserted}/{len(vendors_data)} записей"
                )
            except Exception as batch_error:
                print(f"❌ Ошибка при вставке батча {i//batch_size + 1}:")
                print(f"Ошибка: {batch_error}")
                print(f"Первая запись батча: {json.dumps(batch[0] if batch else {}, ensure_ascii=False, indent=2)}")
                raise

        print(f"🎉 Загрузка завершена! Всего загружено: {total_inserted} записей")

    except FileNotFoundError:
        print(f"❌ Файл {json_file} не найден")
    except Exception as e:
        print(f"❌ Ошибка при выполнении скрипта: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

