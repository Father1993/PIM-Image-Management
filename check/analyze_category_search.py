#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для анализа поиска категорий по хлебным крошкам
Помогает найти почему категория не находится
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

PIM_API_URL = os.getenv("PRODUCT_BASE")
PIM_LOGIN = os.getenv("LOGIN_TEST")
PIM_PASSWORD = os.getenv("PASSWORD_TEST")
CATALOG_1C_ID = 22


def authenticate():
    """Авторизация в PIM API"""
    response = requests.post(
        f"{PIM_API_URL}/sign-in/",
        json={"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
    )
    response.raise_for_status()
    return response.json()["data"]["access"]["token"]


def load_categories(token):
    """Загрузка каталога с построением всех путей"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{PIM_API_URL}/catalog/22", headers=headers)
    response.raise_for_status()
    
    catalog_data = response.json()["data"]
    categories_map = {}
    categories_by_path = {}
    
    def parse_catalog(catalog, parent_path=""):
        current_name = catalog["header"].strip().lower()
        
        if parent_path:
            full_path = f"{parent_path} / {current_name}"
        else:
            full_path = current_name
        
        category_info = {
            "id": catalog["id"],
            "header": catalog["header"],
            "full_path": full_path
        }
        
        categories_map[current_name] = category_info
        categories_by_path[full_path] = category_info
        
        for child in catalog.get("children", []):
            parse_catalog(child, full_path)
    
    parse_catalog(catalog_data)
    return categories_map, categories_by_path


def normalize_category_name(name):
    """Нормализация названия категории для поиска"""
    normalized = name.strip().lower()
    normalized = " ".join(normalized.split())
    return normalized


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


def search_category(breadcrumbs, categories_map, categories_by_path):
    """Поиск категории с детальным выводом"""
    print(f"\n🔍 Поиск категории для: '{breadcrumbs}'")
    print("=" * 60)
    
    if not breadcrumbs:
        print("❌ Хлебные крошки пустые")
        return None
    
    normalized = " / ".join([normalize_category_name(p) for p in breadcrumbs.split("/")])
    print(f"📋 Нормализованные крошки: '{normalized}'")
    
    # Поиск по полному пути
    print(f"\n1️⃣ Поиск по полному пути...")
    if normalized in categories_by_path:
        cat = categories_by_path[normalized]
        print(f"   ✅ НАЙДЕНО: {cat['header']} (ID: {cat['id']}, путь: {cat['full_path']})")
        return cat
    else:
        print(f"   ❌ Не найдено")
    
    # Поиск по частям
    print(f"\n2️⃣ Поиск по частям (от конца)...")
    parts = [normalize_category_name(p) for p in breadcrumbs.split("/")]
    for i, part in enumerate(reversed(parts)):
        print(f"   Проверяем часть {i+1}: '{part}'")
        if part in categories_map:
            cat = categories_map[part]
            print(f"   ✅ НАЙДЕНО: {cat['header']} (ID: {cat['id']}, путь: {cat['full_path']})")
            return cat
        else:
            print(f"   ❌ Не найдено")
    
    # Поиск похожих
    print(f"\n3️⃣ Поиск похожих категорий...")
    last_part = parts[-1] if parts else ""
    if last_part:
        print(f"   Ищем категории, содержащие '{last_part}':")
        found_similar = []
        for path, cat in categories_by_path.items():
            if last_part in path.lower():
                found_similar.append((path, cat))
        
        if found_similar:
            print(f"   Найдено {len(found_similar)} похожих категорий:")
            for path, cat in found_similar[:10]:  # Показываем первые 10
                print(f"      - {cat['header']} (ID: {cat['id']})")
                print(f"        Путь: {path}")
        else:
            print(f"   ❌ Похожих категорий не найдено")
        
        # Поиск с вариациями
        print(f"\n4️⃣ Поиск с вариациями названия...")
        similar = find_similar_category(last_part, categories_map, categories_by_path)
        if similar:
            print(f"   ✅ НАЙДЕНО похожую категорию: {similar['header']} (ID: {similar['id']}, путь: {similar['full_path']})")
            return similar
        else:
            print(f"   ❌ Похожих категорий не найдено")
    
    print(f"\n❌ Категория не найдена")
    return None


def main():
    if len(sys.argv) < 2:
        print("Использование: python analyze_category_search.py 'Хлебные крошки'")
        print("Пример: python analyze_category_search.py 'Изделие из плоск. листа / Уголки'")
        return
    
    breadcrumbs = sys.argv[1]
    
    print("🔐 Авторизация в PIM API...")
    token = authenticate()
    print("✅ Авторизация успешна\n")
    
    print("📂 Загрузка категорий...")
    categories_map, categories_by_path = load_categories(token)
    print(f"✅ Загружено {len(categories_map)} категорий (по именам)")
    print(f"✅ Загружено {len(categories_by_path)} категорий (по путям)\n")
    
    # Поиск категории
    result = search_category(breadcrumbs, categories_map, categories_by_path)
    
    if result:
        print(f"\n✅ Результат: {result['header']} (ID: {result['id']})")
    else:
        print(f"\n❌ Категория не найдена, будет использована корневая")


if __name__ == "__main__":
    main()

