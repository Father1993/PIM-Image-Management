#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки заполненности поля matrix в таблице products
"""

import os
from supabase import create_client
from dotenv import load_dotenv
from collections import Counter

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def main():
    try:
        # Подключение к Supabase
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Подключение к базе данных установлено")

        # Получаем все товары
        print("📊 Загрузка товаров из базы...")
        response = client.table("products").select("id, code_1c, matrix").execute()
        products = response.data or []
        
        total = len(products)
        with_matrix = 0
        without_matrix = 0
        matrix_values = []
        
        for product in products:
            matrix = product.get("matrix")
            if matrix and str(matrix).strip():
                with_matrix += 1
                matrix_values.append(str(matrix).strip())
            else:
                without_matrix += 1
        
        # Статистика по значениям matrix
        matrix_counter = Counter(matrix_values)
        
        print(f"\n📊 Статистика по полю matrix:")
        print(f"   Всего товаров: {total}")
        print(f"   С matrix: {with_matrix} ({with_matrix*100//total}%)")
        print(f"   Без matrix: {without_matrix} ({without_matrix*100//total}%)")
        
        if matrix_counter:
            print(f"\n📋 Распределение значений matrix:")
            for value, count in matrix_counter.most_common():
                print(f"   '{value}': {count} товаров ({count*100//total}%)")
        
        if without_matrix > 0:
            print(f"\n⚠️ Найдено {without_matrix} товаров без matrix")
            # Показываем примеры товаров без matrix
            examples = []
            for product in products:
                matrix = product.get("matrix")
                if not matrix or not str(matrix).strip():
                    examples.append({
                        "id": product.get("id"),
                        "code_1c": product.get("code_1c")
                    })
                    if len(examples) >= 5:
                        break
            
            if examples:
                print(f"   Примеры товаров без matrix (первые 5):")
                for ex in examples:
                    print(f"      ID: {ex['id']}, Code: {ex['code_1c']}")
        else:
            print(f"\n✅ Все товары имеют заполненное поле matrix!")
        
        print(f"\n✅ Проверка завершена")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

