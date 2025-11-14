#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для выгрузки всех товаров из Compo PIM API с использованием scroll метода
Сохраняет все товары в JSON файл
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Конфигурация
PIM_API_URL = os.getenv("PIM_API_URL", "https://pim.uroven.pro/api/v1")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")


def authenticate():
    """Авторизация в PIM API и получение токена"""
    print("[🔐] Авторизация в PIM API...")
    
    response = requests.post(
        f"{PIM_API_URL}/sign-in/",
        json={
            "login": PIM_LOGIN, 
            "password": PIM_PASSWORD, 
            "remember": True
        },
        timeout=30
    )
    
    response.raise_for_status()
    data = response.json()
    
    if data.get("success"):
        print("[✅] Авторизация успешна")
        return data["data"]["access"]["token"]
    else:
        raise Exception(f"[❌] Ошибка авторизации: {data}")


def fetch_all_products_scroll(token):
    """Получить все товары с использованием scroll API"""
    print("[🔄] Начинаем загрузку всех товаров через scroll API...")
    
    headers = {"Authorization": f"Bearer {token}"}
    all_products = []
    scroll_id = None
    total_fetched = 0
    batch_num = 0
    
    while True:
        batch_num += 1
        print(f"[📥] Загрузка партии #{batch_num}...", end="", flush=True)
        
        # Формируем URL в зависимости от наличия scroll_id
        if scroll_id:
            url = f"{PIM_API_URL}/product/scroll/?scrollId={scroll_id}"
        else:
            url = f"{PIM_API_URL}/product/scroll"
        
        response = requests.get(url, headers=headers, timeout=60)
        
        if response.status_code != 200:
            print(f"\n[❌] Ошибка запроса: {response.status_code}")
            break
            
        data = response.json()
        
        if not data.get("success"):
            print(f"\n[❌] Ошибка в ответе API: {data}")
            break
        
        # Извлекаем данные
        response_data = data.get("data", {})
        products = response_data.get("products", [])  # Основное поле с товарами
        new_scroll_id = response_data.get("scrollId")
        
        # Если вдруг используется другое поле (как в некоторых скриптах)
        if not products:
            products = response_data.get("productElasticDtos", [])
        
        if products:
            all_products.extend(products)
            count = len(products)
            total_fetched += count
            print(f" [✅] Получено {count} товаров (всего: {total_fetched})")
        else:
            print(" [✅] Нет больше товаров")
            break
        
        # Обновляем scroll_id для следующего запроса
        scroll_id = new_scroll_id
        
        # Если нет нового scroll_id, значит больше нет данных
        if not new_scroll_id:
            print("[🏁] Достигнут конец списка товаров")
            break
    
    return all_products


def save_products_to_json(products, filename=None):
    """Сохранить товары в JSON файл"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"all_pim_products_{timestamp}.json"
    
    print(f"[💾] Сохраняем {len(products)} товаров в файл: {filename}")
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        print(f"[✅] Файл успешно сохранен: {filename}")
        return filename
    except Exception as e:
        print(f"[❌] Ошибка при сохранении в JSON: {e}")
        raise


def main():
    """Основная функция"""
    print("[📦] Скрипт выгрузки всех товаров из Compo PIM API")
    print(f"🔗 API URL: {PIM_API_URL}\n")
    
    # Проверяем наличие необходимых переменных окружения
    if not all([PIM_LOGIN, PIM_PASSWORD]):
        print("[❌] Необходимо установить переменные окружения PIM_LOGIN и PIM_PASSWORD")
        return
    
    try:
        # Авторизация
        token = authenticate()
        
        # Загрузка всех товаров
        products = fetch_all_products_scroll(token)
        
        if products:
            print(f"\n📊 Всего загружено товаров: {len(products)}")
            
            # Сохранение в JSON
            filename = save_products_to_json(products)
            
            print(f"\n🎉 Завершено! Товары сохранены в файл: {filename}")
        else:
            print("\n❌ Не удалось загрузить товары")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка подключения: {e}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()