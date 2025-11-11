#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки товаров в JSON файле из 1С
"""

import json
import os

JSON_FILE = "Catalog-Pim_01.11.25.json"


def main():
    try:
        print(f"📂 Загрузка файла {JSON_FILE}...")
        with open(JSON_FILE, "r", encoding="utf-8-sig") as f:
            products = json.load(f)
        
        print(f"✅ Загружено товаров: {len(products)}\n")
        
        # Статистика
        total = len(products)
        with_code = 0
        without_code = 0
        with_name = 0
        without_name = 0
        with_barcode = 0
        without_barcode = 0
        with_vendor = 0
        without_vendor = 0
        with_matrix = 0
        without_matrix = 0
        unique_codes = set()
        duplicate_codes = []
        code_counts = {}
        
        for product in products:
            code = product.get("Code", "").strip()
            name = product.get("Name", "").strip()
            barcode = product.get("Barcode", [])
            vendor = product.get("Vendor", [])
            matrix = product.get("Matrix", "").strip()
            
            # Подсчет
            if code:
                with_code += 1
                if code in unique_codes:
                    duplicate_codes.append(code)
                    code_counts[code] = code_counts.get(code, 1) + 1
                else:
                    unique_codes.add(code)
                    code_counts[code] = 1
            else:
                without_code += 1
            
            if name:
                with_name += 1
            else:
                without_name += 1
            
            if barcode and len([b for b in barcode if str(b).strip()]) > 0:
                with_barcode += 1
            else:
                without_barcode += 1
            
            if vendor and len([v for v in vendor if str(v).strip()]) > 0:
                with_vendor += 1
            else:
                without_vendor += 1
            
            if matrix:
                with_matrix += 1
            else:
                without_matrix += 1
        
        # Вывод статистики
        print("📊 Статистика по товарам:")
        print(f"   Всего товаров: {total}")
        print(f"   Уникальных кодов (Code): {len(unique_codes)}")
        print(f"   Дубликатов кодов: {len(set(duplicate_codes))}")
        if duplicate_codes:
            print(f"   Примеры дубликатов: {list(set(duplicate_codes))[:5]}")
        
        print(f"\n📋 Заполненность полей:")
        print(f"   С кодом (Code): {with_code} ({with_code*100//total}%)")
        print(f"   Без кода: {without_code} ({without_code*100//total}%)")
        print(f"   С названием (Name): {with_name} ({with_name*100//total}%)")
        print(f"   Без названия: {without_name} ({without_name*100//total}%)")
        print(f"   Со штрих-кодом (Barcode): {with_barcode} ({with_barcode*100//total}%)")
        print(f"   Без штрих-кода: {without_barcode} ({without_barcode*100//total}%)")
        print(f"   С поставщиком (Vendor): {with_vendor} ({with_vendor*100//total}%)")
        print(f"   Без поставщика: {without_vendor} ({without_vendor*100//total}%)")
        print(f"   С матрицей (Matrix): {with_matrix} ({with_matrix*100//total}%)")
        print(f"   Без матрицы: {without_matrix} ({without_matrix*100//total}%)")
        
        # Примеры товаров
        print(f"\n📦 Примеры товаров:")
        for i, product in enumerate(products[:3], 1):
            print(f"\n   Товар {i}:")
            print(f"      Code: {product.get('Code', 'нет')}")
            print(f"      Name: {product.get('Name', 'нет')}")
            print(f"      Barcode: {product.get('Barcode', [])}")
            print(f"      Vendor: {product.get('Vendor', [])}")
            print(f"      Matrix: {product.get('Matrix', 'нет')}")
        
    except FileNotFoundError:
        print(f"❌ Файл {JSON_FILE} не найден")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

