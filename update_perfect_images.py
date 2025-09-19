#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для обновления поля is_perfect = true в таблице product_images
для товаров из Excel файла products_reference_750x1000.xlsx
"""

import os
import asyncio
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Конфигурация Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Проверяем наличие необходимых переменных окружения
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Ошибка: Не найдены переменные окружения SUPABASE_URL или SUPABASE_KEY")
    exit(1)


class PerfectImageUpdater:
    def __init__(self):
        self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.table_name = None

    def find_product_images_table(self):
        """Найти таблицу product_images в Supabase"""
        possible_names = [
            "product_images",
            "ProductImages",
            "productImages",
            "product_image",
        ]

        for table_name in possible_names:
            try:
                # Тестовый запрос к таблице
                test = self.client.table(table_name).select("id").limit(1).execute()
                self.table_name = table_name
                print(f"✅ Найдена таблица: {table_name}")
                return True
            except Exception as e:
                print(f"⚠️ Таблица {table_name} не найдена: {e}")
                continue

        print("❌ Таблица product_images не найдена!")
        return False

    def read_excel_file(self, file_path):
        """Чтение Excel файла с ID товаров"""
        try:
            # Читаем Excel файл
            df = pd.read_excel(file_path)
            print(f"📂 Файл {file_path} успешно прочитан")
            print(f"📊 Колонки в файле: {df.columns.tolist()}")
            print(f"📝 Общее количество строк: {len(df)}")

            # Ищем колонку с ID товаров
            id_column = None
            possible_id_columns = [
                "id",
                "ID",
                "Id",
                "product_id",
                "ID товара",
                "товар_id",
            ]

            for col in possible_id_columns:
                if col in df.columns:
                    id_column = col
                    break

            if not id_column:
                # Если не нашли по имени, берем первую колонку
                id_column = df.columns[0]
                print(
                    f"⚠️ Не найдена колонка с ID, используем первую колонку: {id_column}"
                )

            print(f"🔍 Используем колонку: {id_column}")

            # Фильтруем данные - оставляем только строки с числовыми ID
            valid_rows = []
            for index, value in df[id_column].items():
                if pd.notna(value):  # Пропускаем NaN значения
                    try:
                        # Пытаемся преобразовать в int
                        product_id = int(value)
                        if product_id > 0:  # ID должен быть положительным
                            valid_rows.append(product_id)
                    except (ValueError, TypeError):
                        # Пропускаем строки, которые не являются числами
                        print(f"⚠️ Пропускаем строку {index}: '{value}' (не число)")
                        continue

            print(f"✅ Найдено {len(valid_rows)} корректных ID товаров")

            if len(valid_rows) > 0:
                print(f"📝 Первые 10 ID: {valid_rows[:10]}")
                print(f"📝 Последние 10 ID: {valid_rows[-10:]}")

            return valid_rows

        except FileNotFoundError:
            print(f"❌ Файл {file_path} не найден!")
            return []
        except Exception as e:
            print(f"❌ Ошибка чтения файла {file_path}: {e}")
            return []

    async def update_perfect_images_batch(self, product_ids, batch_size=50):
        """Обновление поля is_perfect для товаров пакетами"""
        total_updated = 0
        total_errors = 0

        # Обрабатываем товары пакетами
        for i in range(0, len(product_ids), batch_size):
            batch = product_ids[i : i + batch_size]
            print(
                f"🔄 Обработка пакета {i//batch_size + 1}: товары {i+1}-{min(i+batch_size, len(product_ids))}"
            )

            try:
                # Обновляем все записи для товаров из текущего пакета
                response = (
                    self.client.table(self.table_name)
                    .update({"is_perfect": True})
                    .in_("product_id", batch)
                    .execute()
                )

                updated_count = len(response.data) if response.data else 0
                total_updated += updated_count

                print(
                    f"✅ Пакет {i//batch_size + 1}: обновлено {updated_count} записей"
                )

            except Exception as e:
                print(f"❌ Ошибка обновления пакета {i//batch_size + 1}: {e}")
                total_errors += len(batch)
                continue

            # Небольшая пауза между пакетами
            await asyncio.sleep(0.1)

        return total_updated, total_errors

    async def get_affected_records_count(self, product_ids, batch_size=1000):
        """Получить количество записей, которые будут обновлены (пакетно)"""
        total_count = 0

        # Обрабатываем пакетами, чтобы избежать слишком длинных URL
        for i in range(0, len(product_ids), batch_size):
            batch = product_ids[i : i + batch_size]
            try:
                response = (
                    self.client.table(self.table_name)
                    .select("id", count="exact")
                    .in_("product_id", batch)
                    .execute()
                )

                batch_count = (
                    response.count if hasattr(response, "count") else len(response.data)
                )
                total_count += batch_count

                if i % (batch_size * 5) == 0:  # Показываем прогресс каждые 5 пакетов
                    print(
                        f"🔍 Проверено {min(i + batch_size, len(product_ids))}/{len(product_ids)} товаров..."
                    )

            except Exception as e:
                print(f"⚠️ Ошибка проверки пакета {i//batch_size + 1}: {e}")
                continue

        return total_count

    async def verify_updates(self, product_ids, batch_size=1000):
        """Проверить результаты обновления (пакетно)"""
        perfect_count = 0
        total_count = 0

        # Обрабатываем пакетами
        for i in range(0, len(product_ids), batch_size):
            batch = product_ids[i : i + batch_size]
            try:
                # Проверяем сколько записей стали is_perfect = true
                perfect_response = (
                    self.client.table(self.table_name)
                    .select("id", count="exact")
                    .in_("product_id", batch)
                    .eq("is_perfect", True)
                    .execute()
                )

                batch_perfect = (
                    perfect_response.count
                    if hasattr(perfect_response, "count")
                    else len(perfect_response.data)
                )
                perfect_count += batch_perfect

                # Проверяем общее количество записей для этих товаров
                total_response = (
                    self.client.table(self.table_name)
                    .select("id", count="exact")
                    .in_("product_id", batch)
                    .execute()
                )

                batch_total = (
                    total_response.count
                    if hasattr(total_response, "count")
                    else len(total_response.data)
                )
                total_count += batch_total

            except Exception as e:
                print(f"⚠️ Ошибка проверки пакета {i//batch_size + 1}: {e}")
                continue

        return perfect_count, total_count


async def main():
    """Основная функция"""
    print("🚀 Запуск скрипта обновления поля is_perfect для эталонных изображений")

    updater = PerfectImageUpdater()

    # Поиск таблицы product_images
    if not updater.find_product_images_table():
        return

    # Чтение Excel файла
    excel_file = "products_reference_750x1000.xlsx"
    product_ids = updater.read_excel_file(excel_file)

    if not product_ids:
        print("❌ Не найдены ID товаров для обновления")
        return

    # Проверяем сколько записей будет затронуто
    print(f"\n🔍 Проверяем количество записей в таблице {updater.table_name}...")
    affected_count = await updater.get_affected_records_count(product_ids)
    print(f"📊 Найдено {affected_count} записей для обновления")

    if affected_count == 0:
        print("⚠️ Записи для обновления не найдены")
        return

    # Подтверждение обновления
    print(f"\n⚡ Будет обновлено поле is_perfect = true для {affected_count} записей")
    print(f"📝 Товаров в списке: {len(product_ids)}")

    # Выполняем обновление
    print(f"\n🔄 Начинаем обновление...")
    updated_count, error_count = await updater.update_perfect_images_batch(product_ids)

    # Проверяем результаты
    print(f"\n🔍 Проверяем результаты...")
    perfect_count, total_count = await updater.verify_updates(product_ids)

    # Итоговый отчет
    print(f"\n📊 ИТОГОВЫЙ ОТЧЕТ:")
    print(f"✅ Успешно обновлено: {updated_count} записей")
    print(f"❌ Ошибок: {error_count}")
    print(f"🎯 Записей с is_perfect = true: {perfect_count}")
    print(f"📈 Общее количество записей для этих товаров: {total_count}")

    if perfect_count > 0:
        print(f"\n🎉 Обновление завершено успешно!")
    else:
        print(f"\n⚠️ Что-то пошло не так. Проверьте данные и попробуйте снова.")


if __name__ == "__main__":
    asyncio.run(main())
