#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест создания товара в PIM API
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

PIM_API_URL = os.getenv("PRODUCT_BASE")
PIM_LOGIN = os.getenv("LOGIN_TEST")
PIM_PASSWORD = os.getenv("PASSWORD_TEST")

print("🔐 Авторизация...")
auth_response = requests.post(
    f"{PIM_API_URL}/sign-in/",
    json={"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
)
print(f"Статус авторизации: {auth_response.status_code}")

if auth_response.status_code != 200:
    print(f"❌ Ошибка авторизации: {auth_response.text}")
    exit(1)

token = auth_response.json()["data"]["access"]["token"]
print(f"✅ Токен получен: {token[:20]}...\n")

# Тестовые данные товара (минимальные)
test_product = {
    "header": "ТЕСТОВЫЙ ТОВАР - удалить",
    "barCode": "1234567890",
    "articul": "TEST-001",
    "content": None,
    "description": "Тестовое описание",
    "enabled": True,
    "catalogId": 22,  # Уровень - 1с
    "pos": 500,
    "deleted": False
}

print("📦 Создаём тестовый товар...")
print(f"Данные: {json.dumps(test_product, ensure_ascii=False, indent=2)}\n")

headers = {"Authorization": f"Bearer {token}"}
create_response = requests.post(
    f"{PIM_API_URL}/product/",
    headers=headers,
    json=test_product
)

print(f"Статус создания: {create_response.status_code}")
print(f"Content-Type: {create_response.headers.get('Content-Type')}")
print(f"\nОтвет API:")
print("=" * 80)
print(create_response.text[:1000])
print("=" * 80)

# Попытка парсинга JSON
try:
    result = create_response.json()
    print(f"\n✅ JSON успешно распарсен")
    print(f"Тип result: {type(result)}")
    print(f"result: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    if isinstance(result, dict):
        print(f"\nКлючи в result: {list(result.keys())}")
        if "data" in result:
            print(f"Тип data: {type(result['data'])}")
            if isinstance(result['data'], dict):
                print(f"Ключи в data: {list(result['data'].keys())}")
                if 'id' in result['data']:
                    print(f"\n✅ ID товара: {result['data']['id']}")
except json.JSONDecodeError as e:
    print(f"\n❌ Ошибка парсинга JSON: {e}")

