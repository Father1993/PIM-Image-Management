import requests
from dotenv import load_dotenv
import os
import json

load_dotenv()

# Конфигурация

PRODUCT_BASE = os.getenv("PRODUCT_BASE")
LOGIN = os.getenv("LOGIN_TEST")
PASSWORD = os.getenv("PASSWORD_TEST")
login_data = {"login": LOGIN, "password": PASSWORD, "remember": True}


def get_token():
    """Получение токена авторизации"""
    response = requests.post(f"{PRODUCT_BASE}/sign-in/", json=login_data)
    print("🔐 АВТОРИЗАЦИЯ")
    print(f"Статус: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Успешно! Токен получен")
        return data["data"]["access"]["token"]
    else:
        print(f"❌ Ошибка: {response.json()}")
        return None


def get_product(token, product_id):
    """Получение информации о товаре"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{PRODUCT_BASE}/product/{product_id}", headers=headers)

    print(f"\n📦 ИНФОРМАЦИЯ О ТОВАРЕ {product_id}")
    print(f"Статус: {response.status_code}")

    if response.status_code == 200:
        data = response.json()["data"]
        print(f"✅ Название: {data['header']}")
        print(f"Артикул: {data['articul']}")
        print(f"Бренд: {data['brand']['header']}")
        print(f"Каталог: {data['catalog']['header']}")
        print(f"Цена: {data['price']} руб.")
        print(f"Активен: {'Да' if data['enabled'] else 'Нет'}")

        # Информация о картинке
        if data.get("picture"):
            pic = data["picture"]
            print(f"🖼️ Картинка:")
            print(f"   ID: {pic['id']}")
            print(f"   Имя: {pic['name']}")
            print(f"   Разрешение: {pic['sizeX']}x{pic['sizeY']}")
            print(f"   Тип: {pic['type']}")
        else:
            print("🖼️ Картинка: отсутствует")
    else:
        print(f"❌ Ошибка: {response.json()}")


def delete_picture(token, product_id, picture_id):
    """Удаление картинки"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(
        f"{PRODUCT_BASE}/product/{product_id}/picture/{picture_id}", headers=headers
    )

    print(f"\n🗑️ УДАЛЕНИЕ КАРТИНКИ {picture_id}")
    print(f"Статус: {response.status_code}")

    if response.status_code == 200:
        print("✅ Картинка успешно удалена")
    else:
        print(f"❌ Ошибка: {response.json()}")


def upload_picture(token, product_id, image_path):
    """Загрузка картинки"""
    headers = {"Authorization": f"Bearer {token}"}

    with open(image_path, "rb") as f:
        files = {"file": f}
        response = requests.post(
            f"{PRODUCT_BASE}/product/{product_id}/upload-picture",
            headers=headers,
            files=files,
        )

    print(f"\n📤 ЗАГРУЗКА КАРТИНКИ")
    print(f"Статус: {response.status_code}")

    if response.status_code == 200:
        print("✅ Картинка успешно загружена")
    else:
        print(f"❌ Ошибка: {response.json()}")


def main():
    print("🚀 ЗАПУСК СКРИПТА API\n")

    # Получаем токен
    token = get_token()
    if not token:
        print("❌ Остановка: не удалось получить токен")
        return

    # Получаем информацию о товаре
    product_id = 26886
    get_product(token, product_id)

    # Удаляем картинку
    picture_id = 14478
    # delete_picture(token, product_id, picture_id)

    # Загружаем новую картинку (замените путь на реальный)
    # upload_picture(token, product_id, "img.jpg")

    print("\n✅ ВСЕ ОПЕРАЦИИ ЗАВЕРШЕНЫ")


if __name__ == "__main__":
    main()
