import aiohttp
import asyncio
import os
import base64
from urllib.parse import urlparse
import logging
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Конфиг
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
IMGPROXY_URL = os.getenv("IMGPROXY_URL")
BUCKET_NAME = "optimized"  # бакет для сохранения оптимизированных картинок
BATCH_SIZE = 100  # одновременно обрабатываем по 100 продуктов

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


async def ensure_bucket_exists():
    """Создаём bucket, если он ещё не существует"""
    async with aiohttp.ClientSession() as session:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }
        async with session.get(f"{SUPABASE_URL}/storage/v1/bucket", headers=headers) as resp:
            if resp.status == 200:
                buckets = await resp.json()
                if any(b["name"] == BUCKET_NAME for b in buckets):
                    logger.info(f"✅ Bucket '{BUCKET_NAME}' уже существует")
                    return

        payload = {"name": BUCKET_NAME, "public": True}
        async with session.post(f"{SUPABASE_URL}/storage/v1/bucket", headers=headers, json=payload) as resp:
            if resp.status in (200, 201):
                logger.info(f"📂 Создан новый bucket '{BUCKET_NAME}'")
            else:
                text = await resp.text()
                logger.error(f"❌ Ошибка создания bucket: {resp.status} {text}")


async def optimize_image(session, image_url: str) -> bytes | None:
    """Оптимизируем изображение через imgproxy до 750x1000 с белым фоном"""
    try:
        # Проверяем исходный URL, при 404 пробуем с нижним регистром расширения
        async with session.head(image_url) as check:
            if check.status != 200:
                root, ext = os.path.splitext(image_url)
                if ext and ext.lower() != ext:
                    alt_url = root + ext.lower()
                    async with session.head(alt_url) as check2:
                        if check2.status == 200:
                            image_url = alt_url
                        else:
                            logger.warning(f"Изображение недоступно: {image_url}")
                            return None
                else:
                    logger.warning(f"Изображение недоступно: {image_url}")
                    return None

        # Кодируем URL для imgproxy
        b64_url = base64.urlsafe_b64encode(image_url.encode()).decode().rstrip("=")
        
        # resize:fit - сохранение пропорций, extend:1:ce - белый фон по центру
        imgproxy_url = f"{IMGPROXY_URL}/unsafe/resize:fit:750:1000/extend:1:ce/background:255:255:255/quality:85/{b64_url}.jpg"

        
        # Получаем оптимизированное изображение
        async with session.get(imgproxy_url) as resp:
            if resp.status == 200:
                return await resp.read()
            logger.warning(f"Ошибка imgproxy {resp.status} для {image_url}")
            return None

    except Exception as e:
        logger.error(f"Ошибка при оптимизации {image_url}: {e}")
    return None


async def upload_to_supabase(image_name: str, data: bytes) -> str | None:
    """Загрузка оптимизированного файла в Supabase Storage с папками по датам"""
    try:
        today = datetime.now()
        path = f"{today.year}/{today.month:02d}/{today.day:02d}/{image_name}.JPG"
        options = {"content-type": "image/jpeg", "upsert": "true"}
        try:
            supabase.storage.from_(BUCKET_NAME).upload(path, data, options)
        except Exception as e:
            msg = str(e)    
            if "Duplicate" in msg or "already exists" in msg or "409" in msg:
                # Файл уже существует — считаем как успех
                pass
            else:
                raise

        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(path)
        if isinstance(public_url, str) and public_url.endswith("?"):
            public_url = public_url[:-1]
        return public_url
    except Exception as e:
        logger.error(f"Ошибка загрузки {image_name}: {e}")
        return None


async def process_image(session, product: dict, index: int, total: int):
    """Оптимизация + загрузка одного изображения продукта"""
    product_id = product["id"]
    product_name = product.get("product_name", "")
    image_url = product.get("image_url")
    
    if not image_url or not str(image_url).strip():
        logger.info(f"[{index}/{total}] Пропуск {product_name}: пустой image_url")
        return False
    
    # Формируем имя файла из URL или используем product_id
    url_path = urlparse(image_url).path
    file_from_url = os.path.basename(url_path)
    image_name = os.path.splitext(file_from_url)[0] or f"product_{product_id}"

    logger.info(f"[{index}/{total}] Обработка {product_name or image_name} ({image_url})")

    data = await optimize_image(session, image_url)
    if not data:
        return False

    new_url = await upload_to_supabase(image_name, data)
    if not new_url:
        return False

    supabase.table("products").update(
        {
            "is_optimized": True,
            "optimized_url": new_url,
            "updated_at_image_optimized": datetime.now().isoformat(),
        }
    ).eq("id", product_id).execute()

    logger.info(f"[{index}/{total}] ✅ Успешно: {product_name or image_name} → {new_url}")
    return True


async def main(limit: int | None = None):
    """Основной цикл"""
    logger.info("🚀 Запуск оптимизации картинок из Supabase")

    await ensure_bucket_exists()

    # Запрос продуктов с неоптимизированными изображениями
    query = (
        supabase
        .table("products")
        .select("id, product_name, image_url, is_optimized")
        .or_("is_optimized.is.null,is_optimized.eq.false")
        .not_.is_("image_url", "null")
        .neq("image_url", "")
    )
    if limit:
        query = query.limit(limit)

    products = query.execute().data or []
    logger.info(f"Найдено {len(products)} продуктов для оптимизации")

    if not products:
        logger.info("Нет продуктов для оптимизации")
        return

    async with aiohttp.ClientSession() as session:
        total = len(products)
        processed = 0
        success = 0

        for i in range(0, total, BATCH_SIZE):
            batch = products[i : i + BATCH_SIZE]
            # Создаём задачи с нумерацией для каждого продукта
            tasks = [
                process_image(session, product, i + idx + 1, total)
                for idx, product in enumerate(batch)
            ]
            results = await asyncio.gather(*tasks)
            processed += len(batch)
            success += sum(1 for r in results if r)
            logger.info(f"📊 Прогресс: {success} успешно / {processed} обработано / {total} всего")

    logger.info(f"🎉 Готово: {success}/{len(products)} продуктов оптимизировано")


if __name__ == "__main__":
    import sys

    limit = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else None
    asyncio.run(main(limit))
