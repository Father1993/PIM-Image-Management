#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сравнивает файлы товаров без матрицы из PIM и Supabase.
Находит товары, у которых нет матрицы в PIM, но она есть в Supabase.
"""

import pandas as pd
from datetime import datetime

PIM_FILE = "товары_без_указанного_признака_матрицы.xlsx"
SUPABASE_FILE = "products_without_matrix_supabase_20251208_165312.xlsx"
OUTPUT_FILE = f"products_to_update_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"


def main():
    print("📥 Загрузка файлов...")
    
    # Загружаем файлы
    df_pim = pd.read_excel(PIM_FILE)
    df_supabase = pd.read_excel(SUPABASE_FILE)
    
    print(f"✅ PIM: {len(df_pim)} товаров без матрицы")
    print(f"✅ Supabase: {len(df_supabase)} товаров без матрицы")
    
    # Находим товары, которые есть в PIM (нет матрицы), но которых нет в Supabase (есть матрица)
    ids_pim = set(df_pim["id"].dropna())
    ids_supabase = set(df_supabase["id"].dropna())
    ids_to_update = ids_pim - ids_supabase
    
    # Фильтруем товары из PIM файла
    result = df_pim[df_pim["id"].isin(ids_to_update)][["КОД_1С", "id"]].copy()
    
    print(f"\n📊 Найдено {len(result)} товаров для обновления матрицы")
    print(f"   (нет матрицы в PIM, но есть в Supabase)")
    
    if len(result) == 0:
        print("✅ Нет товаров для обновления")
        return
    
    # Сохраняем результат
    result.to_excel(OUTPUT_FILE, index=False, engine="openpyxl")
    print(f"💾 Результаты сохранены в {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

