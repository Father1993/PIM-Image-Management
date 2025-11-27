#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для импорта товаров из Excel файла onec_catalog.XLSX в Supabase таблицу onec_catalog
"""

import os
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv
import asyncio
from typing import List, Dict

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Маппинг колонок Excel -> Supabase
COLUMN_MAPPING = {
    'Номенклатура': 'product_name',
    'Штрихкод': 'barcode',
    'Характеристика': 'characteristic',
    'Код': 'code_1c',
    'Партнер': 'provider',
    'Артикул': 'article',
    'Вес': 'weight',
    'Объем': 'volume',
    'Длина': 'length',
    'Бренд': 'brand',
    'ФайлКартинки': 'image_file',
    'ПризнакМатрицы': 'matrix',
    'Группа1': 'group1',
    'Группа2': 'group2',
    'Группа3': 'group3',
    'Группа4': 'group4',
    'Группа5': 'group5',
    'Группа6': 'group6',
    'Группа7': 'group7',
    'Группа8': 'group8',
    'Группа9': 'group9',
    'Группа10': 'group10'
}


def prepare_row(row: pd.Series) -> Dict:
    """Подготавливает строку для вставки в базу"""
    record = {}
    
    for excel_col, db_col in COLUMN_MAPPING.items():
        value = row.get(excel_col)
        
        # Обработка пустых значений
        if pd.isna(value) or value == '':
            record[db_col] = None
        # Числовые поля
        elif db_col in ['weight', 'volume', 'length']:
            try:
                record[db_col] = float(value) if value else None
            except:
                record[db_col] = None
        # Текстовые поля
        else:
            record[db_col] = str(value).strip() if value else None
    
    return record


def main():
    excel_file = "onec_catalog.XLSX"
    table_name = "onec_catalog"
    
    try:
        # Подключение к Supabase
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Подключение к Supabase установлено")
        
        # Проверка таблицы
        try:
            client.table(table_name).select("*").limit(1).execute()
            print(f"✅ Таблица '{table_name}' найдена")
        except Exception as e:
            print(f"❌ Таблица '{table_name}' не найдена: {e}")
            return
        
        # Чтение Excel файла
        print(f"📂 Читаю файл {excel_file}...")
        df = pd.read_excel(excel_file)
        print(f"✅ Загружено {len(df)} строк из Excel")
        
        # Подготовка данных
        print("🔄 Подготовка данных...")
        records = []
        for idx, row in df.iterrows():
            record = prepare_row(row)
            records.append(record)
            
            if (idx + 1) % 1000 == 0:
                print(f"   Подготовлено {idx + 1}/{len(df)} записей")
        
        print(f"✅ Подготовлено {len(records)} записей")
        
        # Вставка данных пакетами
        batch_size = 100
        total_inserted = 0
        
        print(f"📝 Начинаю вставку данных пакетами по {batch_size}...")
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            try:
                response = client.table(table_name).insert(batch).execute()
                inserted = len(response.data) if response.data else 0
                total_inserted += inserted
                print(f"   ✅ Вставлено {total_inserted}/{len(records)} записей")
                
            except Exception as e:
                print(f"❌ Ошибка при вставке батча {i//batch_size + 1}:")
                print(f"   Диапазон строк: {i}-{i+len(batch)}")
                print(f"   Ошибка: {e}")
                
                # Пробуем вставить по одной записи из проблемного батча
                print("   🔄 Пробую вставить записи по одной...")
                for j, record in enumerate(batch):
                    try:
                        client.table(table_name).insert([record]).execute()
                        total_inserted += 1
                    except Exception as single_error:
                        print(f"   ❌ Ошибка в записи {i+j}: {single_error}")
                        print(f"      Данные: {record}")
        
        print(f"\n🎉 Импорт завершен!")
        print(f"   Всего вставлено: {total_inserted} из {len(records)} записей")
        
    except FileNotFoundError:
        print(f"❌ Файл {excel_file} не найден")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

