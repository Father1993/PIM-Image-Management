# -*- coding: utf-8 -*-
"""
Скрипт для выгрузки товаров с системными маркерами из API Compo PIM

Необходимые зависимости:
pip install aiohttp pandas python-dotenv tqdm

Запуск: python check_no_tempalte_products.py
"""

import os
import asyncio
import aiohttp
import pandas as pd
import logging
import sys
import argparse
from tqdm import tqdm
from dotenv import load_dotenv
from datetime import datetime

# Инициализация парсера аргументов командной строки
parser = argparse.ArgumentParser(
    description="Скрипт для поиска товаров с системными маркерами в PIM"
)
parser.add_argument(
    "--test",
    action="store_true",
    help="Тестовый режим (проверяет только первую партию товаров)",
)
parser.add_argument(
    "--debug", action="store_true", help="Включить подробное логирование"
)
args = parser.parse_args()

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG if args.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("pim_markers_export.log", mode="a"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()
logger.info("Загружены переменные окружения")

PIM_API_URL = os.getenv("PIM_API_URL")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")

# Проверяем наличие необходимых переменных окружения
if not all([PIM_API_URL, PIM_LOGIN, PIM_PASSWORD]):
    logger.error("Отсутствуют необходимые переменные окружения. Проверьте файл .env")
    missing_vars = []
    if not PIM_API_URL:
        missing_vars.append("PIM_API_URL")
    if not PIM_LOGIN:
        missing_vars.append("PIM_LOGIN")
    if not PIM_PASSWORD:
        missing_vars.append("PIM_PASSWORD")
    logger.error(f"Отсутствуют переменные: {', '.join(missing_vars)}")
    sys.exit(1)


# URL для получения товаров через scroll API
SCROLL_API_URL = PIM_API_URL.rstrip("/") + "/product/scroll"
PIM_ITEM_URL_TEMPLATE = "https://pim.uroven.pro/cabinet/pim/catalog/item/edit/{id}"


# Функция для корректного формирования URL с параметром scrollId
def get_scroll_url(base_url, scroll_id=None):
    """Формирует правильный URL для scroll API"""
    if not scroll_id:
        return base_url
    return f"{base_url}?scrollId={scroll_id}"


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
                    logger.info("Токен получен успешно")
                    return data["data"]["access"]["token"]
            logger.error(f"Ошибка авторизации: {response.status}")
    except Exception as e:
        logger.error(f"Ошибка получения токена: {e}")
    return None


async def fetch_products_with_scroll(session, token, scroll_id=None):
    """Получить партию товаров через scroll API"""
    headers = {"Authorization": f"Bearer {token}"}
    url = get_scroll_url(SCROLL_API_URL, scroll_id)

    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                logger.error(f"Ошибка API: {response.status} - {error_text}")
                return None
    except Exception as e:
        logger.error(f"Ошибка запроса: {e}")
        return None


def has_system_markers(product):
    """Проверить наличие системных маркеров у товара"""
    has_markers = product.get("hasSystemMarker", {})
    return bool(has_markers and any(has_markers.values()))


def extract_marker_info(product):
    """Извлечь информацию о системных маркерах товара"""
    has_markers = product.get("hasSystemMarker", {})
    system_markers = product.get("systemMarkers", [])

    markers_dict = {str(marker.get("id")): marker for marker in system_markers}
    marker_info = {}

    for marker_id, is_active in has_markers.items():
        if is_active and marker_id in markers_dict:
            marker = markers_dict[marker_id]
            marker_info[marker_id] = marker.get("header", f"Маркер {marker_id}")

    return marker_info


async def process_all_products(session, token, start_scroll_id=None, test_mode=False):
    """Обработать все товары через scroll API"""
    products_with_markers = []
    total_products = 0
    scroll_id = start_scroll_id
    batch_count = 0
    empty_batches = 0  # Счетчик пустых партий
    small_batches = 0  # Счетчик маленьких партий
    max_empty_batches = 50  # Максимум пустых партий подряд
    max_small_batches = 10  # Максимум маленьких партий подряд

    logger.info("Начинаем сбор товаров с системными маркерами...")
    pbar = tqdm(desc="Обработка товаров", unit="товар")

    while True:
        batch_count += 1

        # Получаем данные через scroll API
        response_data = await fetch_products_with_scroll(session, token, scroll_id)

        if not response_data or not response_data.get("success"):
            logger.info(f"Ошибка ответа API: {response_data}")
            break

        # Получаем товары и scroll_id для следующего запроса
        data = response_data.get("data", {})
        products = data.get("productElasticDtos", [])  # Исправлено поле!
        scroll_id = data.get("scrollId")

        if len(products) > 0:
            logger.info(f"Партия {batch_count}: найдено {len(products)} товаров")

        # Если нет scroll_id, это последняя страница
        if not scroll_id:
            logger.info("Достигнут конец списка товаров (нет scroll_id)")
            break

        # Проверяем количество товаров в партии
        if not products:
            empty_batches += 1
            small_batches = 0
            if empty_batches >= max_empty_batches:
                logger.info(f"Остановка: получено {empty_batches} пустых партий подряд")
                break
        elif len(products) < 50:  # Маленькая партия (обычно 100)
            empty_batches = 0
            small_batches += 1
            if small_batches >= max_small_batches:
                logger.info(
                    f"Остановка: получено {small_batches} маленьких партий подряд (товары заканчиваются)"
                )
                break
            total_products += len(products)
            pbar.update(len(products))
        else:
            empty_batches = 0  # Сбрасываем счетчики при получении полной партии
            small_batches = 0
            total_products += len(products)
            pbar.update(len(products))

        # Обрабатываем товары с системными маркерами
        batch_markers = 0
        for product in products:
            if has_system_markers(product):
                product_info = {
                    "id": product.get("id"),
                    "name": product.get("fullHeader", product.get("header", "")),
                    "codes_articul": product.get("codes", {}).get("articul", ""),
                    "markers": extract_marker_info(product),
                    "pim_url": PIM_ITEM_URL_TEMPLATE.format(id=product.get("id")),
                }
                products_with_markers.append(product_info)
                batch_markers += 1

        if batch_markers > 0:
            logger.info(
                f"Партия {batch_count}: найдено {batch_markers} товаров с маркерами (всего: {len(products_with_markers)})"
            )
        elif batch_count % 100 == 0:  # Логируем каждые 100 партий для прогресса
            logger.info(
                f"Обработано {batch_count} партий, найдено товаров: {total_products}, с маркерами: {len(products_with_markers)}"
            )

        # В тестовом режиме останавливаемся после обработки первой партии
        if test_mode:
            break

    # Закрываем прогресс-бар
    pbar.close()

    logger.info(
        f"Всего обработано {total_products} товаров, найдено с маркерами: {len(products_with_markers)}"
    )
    return products_with_markers


def save_to_excel(products_with_markers):
    """Сохранить данные о товарах с маркерами в Excel"""
    if not products_with_markers:
        logger.warning("Нет товаров с системными маркерами для сохранения")
        return

    # Создаем DataFrame для основной информации о товарах
    rows = []

    # Собираем все уникальные типы маркеров для создания отдельных колонок
    all_marker_types = set()
    for product in products_with_markers:
        for marker_id in product["markers"].keys():
            all_marker_types.add(marker_id)

    for product in products_with_markers:
        # Базовая информация о товаре
        row = {
            "ID товара": product["id"],
            "Название товара": product["name"],
            "Код из 1С": product.get("codes_articul", ""),
            "Системные маркеры": ", ".join(product["markers"].values()),
            "Ссылка на PIM": product["pim_url"],
        }

        rows.append(row)

    df = pd.DataFrame(rows)

    # Создаем имя файла с текущей датой и временем
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"products_with_system_markers_{timestamp}.xlsx"

    # Сохраняем в Excel
    try:
        df.to_excel(filename, index=False)
        logger.info(f"Данные сохранены в файл: {filename}")
        logger.info(f"Всего товаров с системными маркерами: {len(rows)}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении файла: {e}")
        # Пробуем сохранить в CSV как запасной вариант
        csv_filename = f"products_with_system_markers_{timestamp}.csv"
        try:
            df.to_csv(csv_filename, index=False)
            logger.info(f"Данные сохранены в CSV-файл: {csv_filename}")
        except Exception as csv_error:
            logger.error(f"Ошибка при сохранении CSV: {csv_error}")
            return None

    logger.info(f"Найдено товаров с маркерами: {len(products_with_markers)}")

    return filename


async def main():
    """Основная функция"""
    logger.info("Запуск скрипта для поиска товаров с системными маркерами")

    # Проверяем режим работы
    test_mode = args.test
    if test_mode:
        logger.info("Запуск в тестовом режиме")

    logger.info(f"API URL: {PIM_API_URL}")

    try:
        timeout = aiohttp.ClientTimeout(total=60)  # Устанавливаем таймаут для запросов
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Получаем токен авторизации
            logger.info("Запрашиваем токен авторизации PIM API...")
            token = await get_pim_token(session)
            if not token:
                logger.error(
                    "Не удалось получить токен авторизации PIM API. Проверьте учетные данные и доступность сервера."
                )
                return

            logger.info("Токен авторизации успешно получен")

            # Обрабатываем все товары через scroll API
            products_with_markers = await process_all_products(
                session, token, None, test_mode
            )

            # Сохраняем результаты в Excel
            if products_with_markers:
                filename = save_to_excel(products_with_markers)
                if filename:
                    logger.info(
                        f"Обработка завершена. Результаты сохранены в файл: {filename}"
                    )
            else:
                logger.warning(
                    "Товаров с системными маркерами не найдено — проверьте корректность запросов к API"
                )
    except KeyboardInterrupt:
        logger.warning("Скрипт прерван пользователем")
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка сетевого подключения: {e}")
    except Exception as e:
        import traceback

        logger.error(f"Произошла ошибка: {e}")
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())
