#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверяет наличие значений matrix в таблице products для товаров из JSON файла.
"""

import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = "products"
BATCH_SIZE = 500


def load_product_ids(json_file):
    """Загрузить ID товаров из JSON файла"""
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    products = data.get("products", [])
    return [p["id"] for p in products]


def check_matrix_in_products(client, product_ids):
    """Проверить наличие matrix для товаров"""
    results = {
        "with_matrix": [],
        "without_matrix": [],
        "not_found": []
    }
    
    print(f"📋 Проверка {len(product_ids)} товаров в таблице {TABLE_NAME}...")
    
    # Проверяем батчами
    for i in range(0, len(product_ids), BATCH_SIZE):
        batch_ids = product_ids[i:i + BATCH_SIZE]
        
        response = (
            client.table(TABLE_NAME)
            .select("id,matrix,product_name")
            .in_("id", batch_ids)
            .execute()
        )
        
        found_ids = {row["id"]: row for row in (response.data or [])}
        
        for pim_id in batch_ids:
            if pim_id not in found_ids:
                results["not_found"].append(pim_id)
            else:
                row = found_ids[pim_id]
                matrix = row.get("matrix")
                if matrix and str(matrix).strip():
                    results["with_matrix"].append({
                        "id": pim_id,
                        "matrix": matrix,
                        "product_name": row.get("product_name")
                    })
                else:
                    results["without_matrix"].append({
                        "id": pim_id,
                        "product_name": row.get("product_name")
                    })
        
        print(f"✅ Проверено: {min(i + BATCH_SIZE, len(product_ids))}/{len(product_ids)}")
    
    return results


def main():
    if len(sys.argv) < 2:
        print("❌ Укажите путь к JSON файлу")
        print("Использование: python check_matrix_in_products.py <путь_к_json>")
        sys.exit(1)
    
    json_file = Path(sys.argv[1])
    if not json_file.exists():
        print(f"❌ Файл не найден: {json_file}")
        sys.exit(1)
    
    print(f"📥 Загрузка ID из {json_file}...")
    product_ids = load_product_ids(json_file)
    print(f"✅ Загружено {len(product_ids)} ID товаров\n")
    
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    results = check_matrix_in_products(client, product_ids)
    
    # Статистика
    print(f"\n📊 Результаты проверки:")
    print(f"   ✅ С матрицей: {len(results['with_matrix'])}")
    print(f"   ❌ Без матрицы: {len(results['without_matrix'])}")
    print(f"   ⚠️  Не найдено в таблице: {len(results['not_found'])}")
    
    # Сохраняем результаты
    output_file = json_file.parent / f"{json_file.stem}_matrix_check.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "total_checked": len(product_ids),
            "with_matrix": len(results["with_matrix"]),
            "without_matrix": len(results["without_matrix"]),
            "not_found": len(results["not_found"]),
            "with_matrix_list": results["with_matrix"],
            "without_matrix_list": results["without_matrix"],
            "not_found_list": results["not_found"]
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Результаты сохранены в {output_file}")
    
    # Примеры товаров с матрицей
    if results["with_matrix"]:
        print(f"\n📋 Примеры товаров С матрицей (первые 5):")
        for item in results["with_matrix"][:5]:
            print(f"   - ID: {item['id']}, Matrix: {item['matrix']}, Название: {item.get('product_name', 'N/A')[:50]}")
    
    # Примеры товаров без матрицы
    if results["without_matrix"]:
        print(f"\n📋 Примеры товаров БЕЗ матрицы (первые 5):")
        for item in results["without_matrix"][:5]:
            print(f"   - ID: {item['id']}, Название: {item.get('product_name', 'N/A')[:50]}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"❌ Критическая ошибка: {exc}")
        import traceback
        traceback.print_exc()

