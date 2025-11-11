#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания новых товаров (is_new=true) из Supabase в Compo PIM
"""

import os
import sys
import json
import requests
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Конфигурация
PIM_API_URL = os.getenv("PRODUCT_BASE")
PIM_LOGIN = os.getenv("LOGIN_TEST")
PIM_PASSWORD = os.getenv("PASSWORD_TEST")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
CATALOG_1C_ID = 22  # ID каталога "Уровень - 1с"

# Лимит товаров для обработки (None = все)
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else None


def authenticate():
    """Авторизация в PIM API"""
    response = requests.post(
        f"{PIM_API_URL}/sign-in/",
        json={"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
    )
    response.raise_for_status()
    return response.json()["data"]["access"]["token"]


def normalize_category_name(name):
    """Нормализация названия категории для поиска"""
    # Приводим к нижнему регистру и убираем лишние пробелы
    normalized = name.strip().lower()
    # Заменяем множественные пробелы на один
    normalized = " ".join(normalized.split())
    return normalized


def load_categories(token):
    """Загрузка каталога "Уровень - 1с" из PIM API"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{PIM_API_URL}/catalog/22", headers=headers)
    response.raise_for_status()
    
    catalog_data = response.json()["data"]
    categories_map = {}  # По имени -> полный объект категории
    categories_by_path = {}  # По полному пути -> полный объект категории
    root_category = None  # Корневая категория "Уровень - 1с"
    
    def parse_catalog(catalog, parent_path=""):
        """Рекурсивный обход дерева категорий с построением полных путей"""
        current_name = normalize_category_name(catalog["header"])
        
        # Формируем полный путь категории
        if parent_path:
            full_path = f"{parent_path} / {current_name}"
        else:
            full_path = current_name
        
        # Сохраняем полный объект категории
        category_info = {
            "id": catalog["id"],
            "header": catalog["header"],
            "syncUid": catalog.get("syncUid"),
            "parentId": catalog.get("parentId"),
            "enabled": catalog.get("enabled", True),
            "full_path": full_path  # Добавляем полный путь
        }
        
        # Сохраняем по имени (для обратной совместимости)
        categories_map[current_name] = category_info
        
        # Сохраняем по полному пути (для точного поиска)
        categories_by_path[full_path] = category_info
        
        # Сохраняем корневую категорию
        if catalog["id"] == CATALOG_1C_ID:
            nonlocal root_category
            root_category = category_info
        
        # Обрабатываем детей с передачей текущего пути
        for child in catalog.get("children", []):
            parse_catalog(child, full_path)
    
    parse_catalog(catalog_data)
    
    # Если корневая категория не найдена, создаем её из известных данных
    if not root_category:
        root_category = {
            "id": CATALOG_1C_ID,
            "header": "Уровень - 1с",
            "syncUid": "a91bf1b0-024b-4c4d-83d6-d73ec08e9498",
            "parentId": 1,
            "enabled": True,
            "full_path": "уровень - 1с"
        }
    
    return categories_map, categories_by_path, root_category


def create_category(token, header, parent_id=CATALOG_1C_ID):
    """Создание категории в PIM"""
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "id": 0,
        "parentId": parent_id,
        "header": header,
        "enabled": True,
        "deleted": False,
        "lastLevel": True,
        "pos": 500
    }
    
    try:
        response = requests.post(
            f"{PIM_API_URL}/catalog/rapid",
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result.get("success", False)
    except Exception:
        return False


def ensure_category_path(token, breadcrumbs, categories_map, categories_by_path, root_category, debug=False):
    """Создает цепочку категорий, если они не существуют"""
    if not breadcrumbs:
        return None
    
    parts = [p.strip() for p in breadcrumbs.split("/")]
    current_parent_id = root_category["id"]
    current_path = ""
    
    for part in parts:
        normalized_part = normalize_category_name(part)
        current_path = f"{current_path} / {normalized_part}" if current_path else normalized_part
        
        if current_path in categories_by_path:
            current_parent_id = categories_by_path[current_path]["id"]
            continue
        
        if debug:
            print(f"      📝 Создаем категорию: '{part}' (родитель ID: {current_parent_id})")
        
        if create_category(token, part, current_parent_id):
            # Перезагружаем категории для получения ID новой категории
            new_map, new_paths, _ = load_categories(token)
            categories_map.clear()
            categories_map.update(new_map)
            categories_by_path.clear()
            categories_by_path.update(new_paths)
            
            if current_path in categories_by_path:
                current_parent_id = categories_by_path[current_path]["id"]
                if debug:
                    print(f"      ✅ Категория создана: '{part}' (ID: {current_parent_id})")
            else:
                if debug:
                    print(f"      ⚠️  Категория создана, но не найдена при перезагрузке")
                return None
        else:
            if debug:
                print(f"      ❌ Не удалось создать категорию: '{part}'")
            return None
    
    return categories_by_path.get(current_path)


def find_similar_category(search_term, categories_map, categories_by_path):
    """Поиск похожей категории по частичному совпадению"""
    search_term = normalize_category_name(search_term)
    
    # Варианты поиска
    search_variants = [
        search_term,
        search_term.replace("ы", ""),  # уголки -> уголок
        search_term.replace("и", ""),  # уголки -> уголк
        search_term.replace(" ", ""),  # убираем пробелы
    ]
    
    # Ищем точное совпадение
    for variant in search_variants:
        if variant in categories_map:
            return categories_map[variant]
    
    # Ищем частичное совпадение в названиях
    for cat_name, cat_info in categories_map.items():
        if search_term in cat_name or cat_name in search_term:
            return cat_info
    
    # Ищем в полных путях
    for path, cat_info in categories_by_path.items():
        if search_term in path.lower():
            return cat_info
    
    return None


def find_category_by_breadcrumbs(breadcrumbs, categories_map, categories_by_path, token=None, root_category=None, debug=False):
    """
    Поиск категории по хлебным крошкам. Если не найдена - создает её.
    Возвращает объект категории или None (тогда используется корневая)
    """
    if not breadcrumbs:
        if debug:
            print(f"      ⚠️  Хлебные крошки пустые")
        return None
    
    normalized_breadcrumbs = " / ".join([normalize_category_name(p) for p in breadcrumbs.split("/")])
    
    if debug:
        print(f"      🔍 Ищем категорию для: '{normalized_breadcrumbs}'")
    
    # Поиск по полному пути
    if normalized_breadcrumbs in categories_by_path:
        if debug:
            print(f"      ✅ Найдено по полному пути: {categories_by_path[normalized_breadcrumbs]['header']}")
        return categories_by_path[normalized_breadcrumbs]
    
    # Поиск по частям
    parts = [normalize_category_name(p) for p in breadcrumbs.split("/")]
    for part in reversed(parts):
        if part in categories_map:
            found_category = categories_map[part]
            if debug:
                print(f"      ✅ Найдено по части '{part}': {found_category['header']} (ID: {found_category['id']})")
            return found_category
    
    # Поиск похожих
    for part in reversed(parts):
        similar = find_similar_category(part, categories_map, categories_by_path)
        if similar:
            if debug:
                print(f"      ✅ Найдено похожую категорию для '{part}': {similar['header']} (ID: {similar['id']})")
            return similar
    
    # Если не найдено и есть token - создаем категорию
    if token and root_category:
        if debug:
            print(f"      📝 Категория не найдена, создаем...")
        created = ensure_category_path(token, breadcrumbs, categories_map, categories_by_path, root_category, debug)
        if created:
            return created
    
    if debug:
        print(f"      ❌ Категория не найдена, будет использована корневая")
    return None


def prepare_product_data(product, category_obj, root_category):
    """
    Подготовка данных товара для PIM API
    ВАЖНО: Теги (productTags, productSystemTags) НЕ добавляются,
    так как они создаются неправильно в PIM
    """
    # Обработка barcode - если есть, объединяем через запятую
    barcode_value = None
    if product.get("barcode"):
        barcode = product["barcode"]
        
        # Если barcode - строка JSON, парсим её
        if isinstance(barcode, str):
            try:
                barcode = json.loads(barcode)
            except (json.JSONDecodeError, ValueError):
                # Если не JSON, используем как есть
                barcode_value = barcode.strip() if barcode else None
        
        # Если barcode - список, объединяем через запятую
        if isinstance(barcode, list):
            barcode_value = ", ".join(str(b).strip() for b in barcode if b)
        elif barcode_value is None and barcode:
            barcode_value = str(barcode).strip()
    
    # Формируем объект каталога
    if category_obj:
        catalog_obj = {
            "id": category_obj["id"],
            "header": category_obj["header"],
            "syncUid": category_obj.get("syncUid"),
            "parentId": category_obj.get("parentId", CATALOG_1C_ID),
            "enabled": category_obj.get("enabled", True)
        }
    else:
        # Используем корневую категорию "Уровень - 1с"
        catalog_obj = {
            "id": root_category["id"],
            "header": root_category["header"],
            "syncUid": root_category.get("syncUid"),
            "parentId": root_category.get("parentId", 1),
            "enabled": root_category.get("enabled", True)
        }
    
    # Базовые данные товара
    data = {
        "id": 0,
        "header": product.get("product_name") or "Товар без названия",
        "headerAuto": None,
        "fullHeader": None,
        "barCode": barcode_value,
        "articul": product.get("article") or product.get("code_1c"),
        "content": None,
        "description": product.get("description"),
        "price": 0,
        "priceRic": 0,
        "enabled": True,
        "syncUid": None,
        "catalog": catalog_obj,
        "catalogId": catalog_obj["id"],
        "pos": 500,
        "deleted": False
    }
    
    # Добавляем размеры если есть
    if product.get("length"):
        try:
            data["length"] = float(str(product["length"]).replace(",", "."))
        except (ValueError, TypeError):
            pass
    
    if product.get("volume"):
        try:
            data["volume"] = float(str(product["volume"]).replace(",", "."))
        except (ValueError, TypeError):
            pass
    
    if product.get("mass"):
        try:
            data["weight"] = float(str(product["mass"]).replace(",", "."))
        except (ValueError, TypeError):
            pass
    
    return data


def create_product_in_pim(token, product_data):
    """Создание товара в PIM через API"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(
            f"{PIM_API_URL}/product/",
            headers=headers,
            json=product_data,
            timeout=30
        )
        
        # Проверяем статус код
        if response.status_code >= 400:
            return {
                "success": False,
                "message": f"HTTP {response.status_code}: {response.text[:300]}"
            }
        
        # Парсим JSON ответ
        try:
            result = response.json()
            return result
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "message": f"Ошибка парсинга JSON: {str(e)}, Response: {response.text[:300]}"
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"Ошибка запроса: {str(e)}"
        }


def find_product_by_articul(token, articul, catalog_id=CATALOG_1C_ID):
    """Поиск товара в PIM по артикулу для предотвращения дубликатов"""
    if not articul:
        return None
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # Используем scroll API для поиска по всем товарам
        # Первый запрос - получаем scrollId
        url = f"{PIM_API_URL}/product/scroll"
        params = {"catalogId": catalog_id}
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("data"):
                scroll_id = data["data"].get("scrollId")
                products = data["data"].get("products", [])
                
                # Проверяем первую порцию товаров
                for product in products:
                    if str(product.get("articul", "")).strip() == str(articul).strip():
                        return product
                
                # Если не нашли, продолжаем поиск по scroll
                while scroll_id:
                    url = f"{PIM_API_URL}/product/scroll"
                    params = {"scrollId": scroll_id, "catalogId": catalog_id}
                    response = requests.get(url, headers=headers, params=params, timeout=30)
                    
                    if response.status_code != 200:
                        break
                    
                    data = response.json()
                    if not data.get("success"):
                        break
                    
                    scroll_data = data.get("data", {})
                    products = scroll_data.get("products", [])
                    
                    if not products:  # Больше нет товаров
                        break
                    
                    for product in products:
                        if str(product.get("articul", "")).strip() == str(articul).strip():
                            return product
                    
                    scroll_id = scroll_data.get("scrollId")
        
        return None
    except Exception:
        return None


def check_product_exists_in_pim(token, pim_id):
    """Проверка существования товара в PIM по ID"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(
            f"{PIM_API_URL}/product/{pim_id}",
            headers=headers,
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("data"):
                return data["data"]
        return None
    except requests.exceptions.RequestException:
        return None


def update_product_in_supabase(client, supabase_id, pim_id, pim_link):
    """
    Обновление товара в Supabase после успешного создания в PIM
    Устанавливает:
    - link_pim: ссылка на товар в PIM
    - push_to_pim: True (товар отправлен в PIM)
    - is_new: False (товар больше не новый, уже создан)
    """
    client.table("products").update({
        "link_pim": pim_link,
        "push_to_pim": True,
        "is_new": False  # Меняем флаг на False после успешного создания
    }).eq("id", supabase_id).execute()


def main():
    # Проверка переменных окружения
    required_vars = ["PRODUCT_BASE", "LOGIN_TEST", "PASSWORD_TEST", "SUPABASE_URL", "SUPABASE_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"❌ Отсутствуют переменные окружения: {', '.join(missing)}")
        print("   Проверьте файл .env")
        return
    
    # Файл лога ошибок
    log_file = f"create_products_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    errors_log = []
    
    try:
        print("🚀 Начинаем создание новых товаров в PIM...\n")
        
        # Подключение к Supabase
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Подключение к Supabase установлено")
        
        # Авторизация в PIM
        print("🔐 Авторизация в PIM API...")
        token = authenticate()
        print("✅ Авторизация успешна\n")
        
        # Загрузка категорий из API
        print("📂 Загрузка каталога 'Уровень - 1с' из PIM...")
        categories_map, categories_by_path, root_category = load_categories(token)
        print(f"✅ Загружено {len(categories_map)} категорий (по именам)")
        print(f"✅ Загружено {len(categories_by_path)} категорий (по полным путям)\n")
        
        # Получение новых товаров (только с is_new=true)
        print("📦 Получение новых товаров из базы (is_new=true)...")
        query = client.table("products").select("*").eq("is_new", True)
        if LIMIT:
            query = query.limit(LIMIT)
            print(f"⚠️  Установлен лимит: {LIMIT} товаров")
        response = query.execute()
        new_products = response.data
        print(f"✅ Найдено {len(new_products)} новых товаров для создания\n")
        
        # Проверка дубликатов в Supabase: находим все товары с link_pim по code_1c
        print("🔍 Проверка дубликатов в Supabase...")
        all_products = client.table("products").select("code_1c, link_pim, id").execute().data
        existing_links = {}  # code_1c -> (pim_id, link_pim)
        for p in all_products:
            code = str(p.get("code_1c", "")).strip()
            link = p.get("link_pim")
            if code and link:
                # Извлекаем PIM ID из ссылки
                try:
                    pim_id = int(link.split("/")[-1])
                    # Сохраняем первый найденный товар с таким code_1c
                    if code not in existing_links:
                        existing_links[code] = (pim_id, link)
                except (ValueError, IndexError):
                    pass
        
        duplicates_in_supabase = sum(1 for p in new_products if str(p.get("code_1c", "")).strip() in existing_links)
        if duplicates_in_supabase > 0:
            print(f"⚠️  Найдено {duplicates_in_supabase} товаров, которые уже имеют link_pim в Supabase")
        print(f"✅ Проверка завершена\n")
        
        if not new_products:
            print("✅ Нет новых товаров для создания (is_new=false или отсутствуют)")
            return
        
        # Создание товаров
        success_count = 0
        error_count = 0
        
        for idx, product in enumerate(new_products, 1):
            try:
                # Проверка типа данных
                if not isinstance(product, dict):
                    raise TypeError(f"Product должен быть dict, получен {type(product)}")
                
                # Проверка флага is_new
                if not product.get("is_new", False):
                    print(f"[{idx}/{len(new_products)}] ⚠️  Пропущен - is_new=false: {product.get('code_1c')}")
                    continue
                
                # Проверка: если уже есть link_pim в Supabase - товар уже создан
                if product.get("link_pim"):
                    print(f"[{idx}/{len(new_products)}] ⚠️  Пропущен - уже есть link_pim: {product.get('link_pim')}")
                    continue
                
                # Проверка дубликатов в Supabase по code_1c
                code_1c = product.get('code_1c', '')
                if code_1c and code_1c in existing_links:
                    existing_id, existing_link = existing_links[code_1c]
                    print(f"[{idx}/{len(new_products)}] ⚠️  ДУБЛИКАТ В SUPABASE!")
                    print(f"   🔢 Код 1С: {code_1c}")
                    print(f"   📦 Существующий товар в PIM: ID={existing_id}")
                    print(f"   🔗 Существующий link_pim: {existing_link}")
                    print(f"   ⚠️  Используем существующий товар вместо создания нового")
                    
                    # Обновляем Supabase, используя существующий товар
                    update_product_in_supabase(client, product["id"], existing_id, existing_link)
                    success_count += 1
                    print(f"   ✅ Связь с существующим товаром установлена")
                    continue
                
                # Проверка дубликатов в PIM (только если не нашли в Supabase)
                if code_1c:
                    print(f"[{idx}/{len(new_products)}] 🔍 Проверяем дубликаты в PIM для кода 1С: {code_1c}...")
                    existing_product = find_product_by_articul(token, code_1c)
                    if existing_product:
                        existing_id = existing_product.get("id")
                        existing_name = existing_product.get("header", "N/A")
                        print(f"   ⚠️  ТОВАР УЖЕ СУЩЕСТВУЕТ В PIM!")
                        print(f"   📦 Существующий товар: {existing_name} (ID: {existing_id})")
                        print(f"   ⚠️  Пропускаем создание, чтобы избежать дубликата")
                        
                        # Обновляем Supabase, используя существующий товар
                        pim_link = f"{PIM_API_URL.replace('/api/v1', '')}/product/{existing_id}"
                        update_product_in_supabase(client, product["id"], existing_id, pim_link)
                        success_count += 1
                        print(f"   ✅ Связь с существующим товаром установлена в Supabase")
                        continue
                    else:
                        print(f"   ✅ Дубликатов не найдено, создаем новый товар")
                
                # Определяем категорию по полному пути хлебных крошек (создаем если не найдена)
                category_obj = find_category_by_breadcrumbs(
                    product.get("product_group"),
                    categories_map,
                    categories_by_path,
                    token=token,
                    root_category=root_category,
                    debug=True
                )
                
                # Логирование результата поиска категории
                if category_obj:
                    category_name = category_obj["header"]
                    category_id = category_obj["id"]
                    category_path = category_obj.get("full_path", "N/A")
                    print(f"      ✅ Категория найдена: {category_name} (ID: {category_id})")
                else:
                    category_name = root_category["header"]
                    category_id = root_category["id"]
                    category_path = "корневая"
                    print(f"      ⚠️  Категория не найдена, используется корневая: {category_name} (ID: {category_id})")
                
                # Подготовка данных
                product_data = prepare_product_data(product, category_obj, root_category)
                
                # Создание в PIM
                product_name = product.get('product_name', 'Без имени')
                code_1c = product.get('code_1c', 'Без кода')
                product_group = product.get('product_group', 'Не указана')
                print(f"[{idx}/{len(new_products)}] {product_name[:50]}...")
                print(f"   📂 Категория: {category_name} (ID: {category_id})")
                print(f"   🗺️  Путь категории: {category_path}")
                print(f"   📋 Хлебные крошки: {product_group}")
                print(f"   🔢 Код 1С: {code_1c}")
                result = create_product_in_pim(token, product_data)
                
                # Отладка: проверяем тип ответа
                if not isinstance(result, dict):
                    error_msg = f"API вернул {type(result).__name__} вместо dict: {str(result)[:200]}"
                    error_count += 1
                    print(f"   ❌ {error_msg}")
                    errors_log.append({
                        "product_id": product.get("id"),
                        "code_1c": product.get("code_1c"),
                        "name": product_name,
                        "error": error_msg,
                        "result_type": str(type(result)),
                        "result_value": str(result)[:500]
                    })
                    continue
                
                if result.get("success"):
                    # API возвращает data как строку с ID, а не объект
                    data = result.get("data")
                    
                    # Извлекаем ID товара
                    if isinstance(data, str):
                        # data это строка с ID: "28174"
                        try:
                            pim_id = int(data)
                        except (ValueError, TypeError):
                            error_msg = f"Не удалось преобразовать ID из строки: {data}"
                            error_count += 1
                            print(f"   ❌ {error_msg}")
                            errors_log.append({
                                "product_id": product.get("id"),
                                "code_1c": product.get("code_1c"),
                                "name": product_name,
                                "error": error_msg,
                                "result": str(result)[:500]
                            })
                            continue
                    elif isinstance(data, dict):
                        # Если вдруг вернулся объект
                        pim_id = data.get("id")
                        if not pim_id:
                            error_msg = "В ответе API нет id товара"
                            error_count += 1
                            print(f"   ❌ {error_msg}")
                            errors_log.append({
                                "product_id": product.get("id"),
                                "code_1c": product.get("code_1c"),
                                "name": product_name,
                                "error": error_msg,
                                "result": str(result)[:500]
                            })
                            continue
                    else:
                        error_msg = f"Неожиданный тип data: {type(data).__name__}, значение: {data}"
                        error_count += 1
                        print(f"   ❌ {error_msg}")
                        errors_log.append({
                            "product_id": product.get("id"),
                            "code_1c": product.get("code_1c"),
                            "name": product_name,
                            "error": error_msg,
                            "result": str(result)[:500]
                        })
                        continue
                    
                    # Проверка: товар действительно создан в PIM
                    created_product = check_product_exists_in_pim(token, pim_id)
                    if not created_product:
                        error_msg = f"Товар создан (ID={pim_id}), но не найден при проверке"
                        error_count += 1
                        print(f"   ❌ {error_msg}")
                        errors_log.append({
                            "product_id": product.get("id"),
                            "code_1c": product.get("code_1c"),
                            "name": product_name,
                            "error": error_msg,
                            "pim_id": pim_id
                        })
                        continue
                    
                    # КРИТИЧЕСКАЯ ПРОВЕРКА: проверяем, не создался ли дубликат
                    # Ищем другие товары с таким же артикулом
                    code_1c = product.get('code_1c', '')
                    if code_1c:
                        # Проверяем в Supabase - есть ли другие товары с таким code_1c и link_pim
                        duplicate_check = client.table("products").select("id, link_pim").eq("code_1c", code_1c).neq("id", product["id"]).execute()
                        duplicates = [p for p in duplicate_check.data if p.get("link_pim")]
                        if duplicates:
                            print(f"   ⚠️  ВНИМАНИЕ: Найдены другие товары в Supabase с таким же code_1c и link_pim!")
                            for dup in duplicates:
                                print(f"      - ID: {dup.get('id')}, link_pim: {dup.get('link_pim')}")
                    
                    # Проверка категории созданного товара
                    created_category_id = created_product.get("catalogId")
                    expected_category_id = category_obj["id"] if category_obj else root_category["id"]
                    
                    # Получаем название категории для вывода
                    created_category_name = "N/A"
                    if created_product.get("catalog"):
                        created_category_name = created_product["catalog"].get("header", "N/A")
                    elif created_product.get("catalogHeader"):
                        created_category_name = created_product.get("catalogHeader")
                    
                    if created_category_id != expected_category_id:
                        error_msg = f"Категория не совпадает! Ожидалось: {expected_category_id}, получено: {created_category_id}"
                        error_count += 1
                        print(f"   ⚠️  {error_msg}")
                        errors_log.append({
                            "product_id": product.get("id"),
                            "code_1c": product.get("code_1c"),
                            "name": product_name,
                            "error": error_msg,
                            "expected_category": expected_category_id,
                            "actual_category": created_category_id,
                            "pim_id": pim_id
                        })
                        # Не обновляем Supabase, если категория неправильная
                        continue
                    
                    pim_link = f"{PIM_API_URL.replace('/api/v1', '')}/product/{pim_id}"
                    
                    # Обновление в Supabase: устанавливаем is_new=False после успешного создания
                    update_product_in_supabase(client, product["id"], pim_id, pim_link)
                    
                    success_count += 1
                    print(f"   ✅ Создан ID={pim_id}, категория проверена: {created_category_name} (ID: {created_category_id})")
                    print(f"   📝 Флаг is_new изменен на False в Supabase")
                else:
                    error_msg = result.get('message', 'Unknown error')
                    error_count += 1
                    print(f"   ❌ {error_msg}")
                    errors_log.append({
                        "product_id": product.get("id"),
                        "code_1c": product.get("code_1c"),
                        "name": product_name,
                        "error": error_msg,
                        "result": str(result)[:500]
                    })
                    
            except Exception as e:
                import traceback
                error_msg = str(e)
                error_traceback = traceback.format_exc()
                error_count += 1
                print(f"   ❌ {error_msg[:100]}")
                errors_log.append({
                    "product_id": product.get("id"),
                    "code_1c": product.get("code_1c"),
                    "name": product.get('product_name', 'Без имени'),
                    "error": error_msg,
                    "traceback": error_traceback
                })
        
        print(f"\n🎉 Готово!")
        print(f"   ✅ Успешно создано: {success_count}")
        print(f"   ❌ Ошибок: {error_count}")
        
        # Сохранение лога ошибок
        if errors_log:
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(errors_log, f, ensure_ascii=False, indent=2)
            print(f"\n📝 Лог ошибок сохранен в: {log_file}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

