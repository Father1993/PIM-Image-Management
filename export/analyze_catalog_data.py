#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для анализа экспортированной структуры каталогов.
Визуализация дерева, статистика, поиск аномалий.
"""

import json
import os
from collections import Counter, defaultdict
from typing import Any


CATALOG_JSON = os.getenv("PIM_CATALOG_OUTPUT", "data/catalog_structure.json")
LINKS_JSON = os.getenv("PIM_PRODUCT_CATALOG_OUTPUT", "data/product_catalog_links.json")


def load_json(filepath: str) -> dict[str, Any]:
    """Загрузка JSON файла."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Файл {filepath} не найден")
    
    with open(filepath, "r", encoding="utf-8") as fh:
        return json.load(fh)


def print_tree(
    catalogs: list[dict],
    parent_id: int | None = None,
    prefix: str = "",
    is_last: bool = True,
    max_depth: int = 3,
    current_depth: int = 0
) -> None:
    """
    Рекурсивная визуализация дерева каталогов.
    
    Args:
        catalogs: Список всех каталогов
        parent_id: ID родителя для текущего уровня
        prefix: Префикс для отступов
        is_last: Последний ли элемент в группе
        max_depth: Максимальная глубина отображения
        current_depth: Текущая глубина
    """
    if current_depth >= max_depth:
        return
    
    # Фильтруем каталоги для текущего уровня
    children = [c for c in catalogs if c.get("parentId") == parent_id]
    children.sort(key=lambda x: (x.get("pos") or 999, x.get("header", "")))
    
    for idx, catalog in enumerate(children):
        is_last_child = (idx == len(children) - 1)
        
        # Определяем символы для отрисовки
        connector = "└── " if is_last_child else "├── "
        
        # Формируем информацию о каталоге
        info_parts = [catalog.get("header", "Без названия")]
        
        if catalog.get("productCountPim", 0) > 0:
            info_parts.append(f"[{catalog['productCountPim']} товаров]")
        
        if not catalog.get("enabled"):
            info_parts.append("❌")
        
        if catalog.get("lastLevel"):
            info_parts.append("🏁")
        
        info = " ".join(info_parts)
        
        # Выводим строку
        print(f"{prefix}{connector}{info}")
        
        # Рекурсивно обрабатываем детей
        extension = "    " if is_last_child else "│   "
        print_tree(
            catalogs,
            catalog.get("id"),
            prefix + extension,
            True,
            max_depth,
            current_depth + 1
        )


def analyze_catalog_structure(data: dict) -> None:
    """Анализ структуры каталогов."""
    catalogs = data.get("catalogs", [])
    statistics = data.get("statistics", {})
    
    print("=" * 80)
    print("📊 АНАЛИЗ СТРУКТУРЫ КАТАЛОГОВ")
    print("=" * 80)
    
    # Общая статистика
    print("\n🔢 Общая статистика:")
    print(f"   • Всего каталогов: {statistics.get('total_catalogs', 0)}")
    print(f"   • Активных: {statistics.get('enabled_catalogs', 0)}")
    print(f"   • Удаленных: {statistics.get('deleted_catalogs', 0)}")
    print(f"   • Конечных (leaf): {statistics.get('leaf_catalogs', 0)}")
    print(f"   • С товарами: {statistics.get('catalogs_with_products', 0)}")
    print(f"   • Максимальная глубина: {statistics.get('max_depth', 0)}")
    print(f"   • Всего товаров: {statistics.get('total_products', 0):,}")
    
    # Распределение по уровням
    levels_dist = statistics.get("levels_distribution", {})
    if levels_dist:
        print("\n📊 Распределение по уровням:")
        for level in sorted(int(k) for k in levels_dist.keys()):
            count = levels_dist[str(level)]
            print(f"   Уровень {level}: {count} каталогов")
    
    # Топ-10 каталогов по количеству товаров
    catalogs_with_products = [
        c for c in catalogs 
        if c.get("productCountPim", 0) > 0
    ]
    catalogs_with_products.sort(key=lambda x: x.get("productCountPim", 0), reverse=True)
    
    if catalogs_with_products:
        print("\n🏆 Топ-10 каталогов по количеству товаров:")
        for idx, catalog in enumerate(catalogs_with_products[:10], 1):
            path = catalog.get("path", "N/A")
            count = catalog.get("productCountPim", 0)
            print(f"   {idx:2d}. {path[:60]:<60} {count:>6} товаров")
    
    # Пустые конечные каталоги
    empty_leaf = [
        c for c in catalogs 
        if c.get("lastLevel") and c.get("productCountPim", 0) == 0 and c.get("enabled")
    ]
    
    if empty_leaf:
        print(f"\n⚠️  Пустые конечные каталоги: {len(empty_leaf)}")
        for catalog in empty_leaf[:5]:
            print(f"   • {catalog.get('path', 'N/A')}")
        if len(empty_leaf) > 5:
            print(f"   ... и еще {len(empty_leaf) - 5}")
    
    # Каталоги без родителя (кроме корневых)
    orphans = [
        c for c in catalogs 
        if c.get("parentId") and c.get("parentId") not in {cat.get("id") for cat in catalogs}
    ]
    
    if orphans:
        print(f"\n⚠️  Каталоги без родителя: {len(orphans)}")
        for catalog in orphans[:5]:
            print(f"   • ID {catalog.get('id')}: {catalog.get('header')}")


def analyze_product_links(data: dict) -> None:
    """Анализ связей товаров с каталогами."""
    links = data.get("links", [])
    products = data.get("products", [])
    statistics = data.get("statistics", {})
    
    print("\n" + "=" * 80)
    print("🔗 АНАЛИЗ СВЯЗЕЙ ТОВАРОВ С КАТАЛОГАМИ")
    print("=" * 80)
    
    # Общая статистика
    print("\n🔢 Общая статистика:")
    print(f"   • Всего товаров: {statistics.get('total_products', 0):,}")
    print(f"   • Всего связей: {statistics.get('total_links', 0):,}")
    print(f"   • Основных категорий: {statistics.get('primary_links', 0):,}")
    print(f"   • Дополнительных категорий: {statistics.get('additional_links', 0):,}")
    print(f"   • Товаров без категорий: {statistics.get('products_without_links', 0):,}")
    print(f"   • Уникальных каталогов: {statistics.get('unique_catalogs', 0)}")
    print(f"   • Среднее категорий на товар: {statistics.get('avg_catalogs_per_product', 0):.2f}")
    
    # Распределение товаров по количеству категорий
    product_category_counts: dict[int, int] = defaultdict(int)
    for product_id in {link["product_id"] for link in links}:
        product_links = [l for l in links if l["product_id"] == product_id]
        product_category_counts[len(product_links)] += 1
    
    if product_category_counts:
        print("\n📊 Распределение товаров по количеству категорий:")
        for count in sorted(product_category_counts.keys())[:10]:
            products_count = product_category_counts[count]
            print(f"   {count} категорий: {products_count:>6} товаров")
    
    # Топ каталогов
    top_catalogs = statistics.get("top_catalogs", [])
    if top_catalogs:
        print("\n🏆 Топ-10 каталогов по количеству товаров:")
        for idx, item in enumerate(top_catalogs[:10], 1):
            cat_id = item.get("catalog_id")
            count = item.get("product_count")
            print(f"   {idx:2d}. Каталог #{cat_id:<6} {count:>6} товаров")
    
    # Товары с множественными категориями
    multi_category_products = [
        pid for pid, count in product_category_counts.items() if count > 3
    ]
    
    if multi_category_products:
        print(f"\n📌 Товары с более чем 3 категориями: {len(multi_category_products)}")
        for product_id in list(multi_category_products)[:5]:
            product_links = [l for l in links if l["product_id"] == product_id]
            product_info = next((p for p in products if p["id"] == product_id), {})
            header = product_info.get("header", "N/A")
            
            print(f"\n   Товар #{product_id}: {header[:50]}")
            print(f"   Категорий: {len(product_links)}")
            for link in product_links[:5]:
                marker = "★" if link.get("is_primary") else "  "
                print(f"      {marker} {link.get('catalog_header', 'N/A')}")


def visualize_tree(data: dict, max_depth: int = 3) -> None:
    """Визуализация дерева каталогов."""
    catalogs = data.get("catalogs", [])
    
    print("\n" + "=" * 80)
    print(f"🌳 ДЕРЕВО КАТАЛОГОВ (глубина до {max_depth} уровней)")
    print("=" * 80)
    print()
    
    print_tree(catalogs, parent_id=None, max_depth=max_depth)


def find_inconsistencies(data: dict) -> None:
    """Поиск несоответствий в данных."""
    catalogs = data.get("catalogs", [])
    
    print("\n" + "=" * 80)
    print("🔍 ПОИСК АНОМАЛИЙ И НЕСООТВЕТСТВИЙ")
    print("=" * 80)
    
    issues = []
    
    # 1. Проверка nested sets
    for catalog in catalogs:
        lft = catalog.get("lft")
        rgt = catalog.get("rgt")
        
        if lft and rgt and lft >= rgt:
            issues.append(f"❌ Каталог #{catalog.get('id')} ({catalog.get('header')}): lft >= rgt")
    
    # 2. Промежуточные каталоги с lastLevel=true
    for catalog in catalogs:
        if catalog.get("lastLevel") and catalog.get("hasChildren"):
            issues.append(
                f"⚠️  Каталог #{catalog.get('id')} ({catalog.get('header')}): "
                f"lastLevel=true но есть дети"
            )
    
    # 3. Неактивные каталоги с товарами
    for catalog in catalogs:
        if not catalog.get("enabled") and catalog.get("productCountPim", 0) > 0:
            issues.append(
                f"⚠️  Каталог #{catalog.get('id')} ({catalog.get('header')}): "
                f"отключен но содержит {catalog.get('productCountPim')} товаров"
            )
    
    # 4. Дублирующиеся syncUid
    sync_uids = [c.get("syncUid") for c in catalogs if c.get("syncUid")]
    duplicates = [uid for uid, count in Counter(sync_uids).items() if count > 1]
    
    for uid in duplicates:
        dups = [c for c in catalogs if c.get("syncUid") == uid]
        issues.append(
            f"❌ Дублирующийся syncUid '{uid}': "
            f"каталоги {', '.join(str(c.get('id')) for c in dups)}"
        )
    
    # Вывод результатов
    if issues:
        print(f"\n⚠️  Найдено проблем: {len(issues)}\n")
        for issue in issues[:20]:
            print(f"   {issue}")
        if len(issues) > 20:
            print(f"\n   ... и еще {len(issues) - 20} проблем")
    else:
        print("\n✅ Аномалий не обнаружено!")


def main():
    """Основная функция."""
    print("\n🔬 АНАЛИЗАТОР ДАННЫХ КАТАЛОГА COMPO PIM\n")
    
    # Проверяем наличие файлов
    catalog_exists = os.path.exists(CATALOG_JSON)
    links_exists = os.path.exists(LINKS_JSON)
    
    if not catalog_exists:
        print(f"❌ Файл {CATALOG_JSON} не найден")
        print("   Запустите: python export/export_catalog_structure.py")
        return
    
    # Загружаем данные
    print("📂 Загрузка данных...\n")
    catalog_data = load_json(CATALOG_JSON)
    
    # Анализируем структуру каталогов
    analyze_catalog_structure(catalog_data)
    
    # Визуализируем дерево
    depth = int(input("\n🌳 Глубина визуализации дерева (1-5, Enter=3): ").strip() or "3")
    visualize_tree(catalog_data, max_depth=min(max(depth, 1), 5))
    
    # Проверяем несоответствия
    find_inconsistencies(catalog_data)
    
    # Анализируем связи товаров, если файл существует
    if links_exists:
        links_data = load_json(LINKS_JSON)
        analyze_product_links(links_data)
    else:
        print(f"\n💡 Для анализа связей товаров запустите:")
        print(f"   python export/export_product_catalog_links.py")
    
    print("\n" + "=" * 80)
    print("✨ Анализ завершен!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

