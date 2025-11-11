#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Отладочный скрипт для проверки структуры данных товаров из Supabase
"""

import os
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Получаем первый новый товар
response = client.table("products").select("*").eq("is_new", True).limit(1).execute()

if response.data:
    product = response.data[0]
    
    print("=== Структура товара ===\n")
    print(f"Тип: {type(product)}")
    print(f"\nПоля товара:")
    
    for key, value in product.items():
        print(f"  {key}: {type(value).__name__} = {repr(value)[:100]}")
    
    print(f"\n\n=== JSON представление ===")
    print(json.dumps(product, ensure_ascii=False, indent=2, default=str))
else:
    print("❌ Новые товары не найдены")

