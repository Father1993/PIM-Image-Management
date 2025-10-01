#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для добавления ссылок PIM в Excel файл products.xlsx
Читает Excel, находит товары в Supabase по code_1c, добавляет link_pim
"""
import os
import pandas as pd
import asyncio
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

# Конфигурация
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


class ExcelPimLinker:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.excel_file = "products.xlsx"

    def read_excel_file(self):
        """Чтение Excel файла и извлечение кодов 1С"""
        try:
            # Читаем Excel файл
            df = pd.read_excel(self.excel_file)
            logger.info(f"Прочитан Excel файл: {len(df)} строк")

            # Проверяем наличие колонки с кодом 1С
            code_1c_column = None
            for col in df.columns:
                if "код" in col.lower() and "1с" in col.lower():
                    code_1c_column = col
                    break

            if not code_1c_column:
                logger.error("Не найдена колонка с кодом 1С в Excel файле")
                return None

            logger.info(f"Найдена колонка с кодом 1С: {code_1c_column}")

            # Извлекаем коды 1С (убираем пустые значения и убираем .0 из чисел)
            codes_1c = df[code_1c_column].dropna().astype(str).tolist()
            codes_1c = [
                code.replace(".0", "") if code.endswith(".0") else code
                for code in codes_1c
                if code.strip()
            ]

            logger.info(f"Извлечено {len(codes_1c)} кодов 1С")
            logger.info(f"Примеры кодов 1С: {codes_1c[:5]}")
            return df, code_1c_column, codes_1c

        except Exception as e:
            logger.error(f"Ошибка при чтении Excel файла: {e}")
            return None

    async def get_link_pim_from_supabase(self, codes_1c):
        """Получение ссылок PIM из Supabase по кодам 1С"""
        try:
            # Определяем название таблицы
            table_names = ["product", "products", "Product", "Products"]
            table_found = None

            for table_name in table_names:
                try:
                    test = (
                        self.supabase.table(table_name).select("id").limit(1).execute()
                    )
                    table_found = table_name
                    logger.info(f"Найдена таблица: {table_name}")
                    break
                except:
                    continue

            if not table_found:
                logger.error("Таблица товаров не найдена в Supabase")
                return {}

            # Получаем товары пакетами (Supabase имеет ограничения на IN запросы)
            batch_size = 100
            all_products = {}

            for i in range(0, len(codes_1c), batch_size):
                batch_codes = codes_1c[i : i + batch_size]

                # Запрос к Supabase
                response = (
                    self.supabase.table(table_found)
                    .select("code_1c, link_pim")
                    .in_("code_1c", batch_codes)
                    .execute()
                )

                # Сохраняем результаты
                for product in response.data:
                    code_1c = product.get("code_1c")
                    link_pim = product.get("link_pim")
                    if code_1c and link_pim:
                        all_products[code_1c] = link_pim

                logger.info(
                    f"Обработано {min(i + batch_size, len(codes_1c))}/{len(codes_1c)} кодов"
                )

            logger.info(f"Найдено {len(all_products)} товаров со ссылками PIM")
            return all_products

        except Exception as e:
            logger.error(f"Ошибка при запросе к Supabase: {e}")
            return {}

    def update_excel_with_links(self, df, code_1c_column, link_pim_data):
        """Добавление колонки с ссылками PIM в Excel"""
        try:
            # Создаем новую колонку для ссылок PIM
            # Преобразуем коды 1С в том же формате что и для поиска
            df_codes_normalized = (
                df[code_1c_column]
                .astype(str)
                .apply(lambda x: x.replace(".0", "") if x.endswith(".0") else x)
            )
            df["Ссылка PIM"] = df_codes_normalized.map(link_pim_data)

            # Подсчитываем статистику
            total_rows = len(df)
            found_links = df["Ссылка PIM"].notna().sum()

            logger.info(f"Добавлено {found_links} ссылок из {total_rows} товаров")

            # Сохраняем обновленный файл
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"products_with_pim_links_{timestamp}.xlsx"

            df.to_excel(output_file, index=False)
            logger.info(f"Сохранен обновленный файл: {output_file}")

            return output_file, found_links, total_rows

        except Exception as e:
            logger.error(f"Ошибка при обновлении Excel файла: {e}")
            return None, 0, 0


async def main():
    """Основная функция"""
    try:
        linker = ExcelPimLinker()

        # Читаем Excel файл
        logger.info("🔍 Чтение Excel файла...")
        excel_data = linker.read_excel_file()
        if not excel_data:
            return

        df, code_1c_column, codes_1c = excel_data

        # Получаем ссылки PIM из Supabase
        logger.info("🔗 Получение ссылок PIM из Supabase...")
        link_pim_data = await linker.get_link_pim_from_supabase(codes_1c)

        if not link_pim_data:
            logger.warning("Не найдено ни одной ссылки PIM")
            return

        # Обновляем Excel файл
        logger.info("📊 Обновление Excel файла...")
        result = linker.update_excel_with_links(df, code_1c_column, link_pim_data)

        if result[0]:  # output_file
            output_file, found_links, total_rows = result
            logger.info(f"✅ Готово! Файл: {output_file}")
            logger.info(f"📈 Статистика: {found_links}/{total_rows} ссылок добавлено")
        else:
            logger.error("❌ Ошибка при создании файла")

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
