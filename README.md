# 🖼️ PIM Image Optimizer через imgproxy

Автоматизация оптимизации изображений товаров: PIM → imgproxy → PIM

## 🚀 Быстрый старт

### 1. Создайте таблицу в Supabase

Выполните SQL из файла `create_product_images_table.sql`

### 2. Запустите в режиме preview

```bash
# Тестовый режим - обработает 1-5 изображений
python optimized.py preview
```

### 3. Полный цикл обработки

```bash
# Сканирование всех изображений
python optimized.py scan

# Оптимизация через imgproxy
python optimized.py optimize

# Загрузка обратно в PIM
python optimized.py upload

# Или все сразу
python optimized.py full
```

## 📋 Режимы работы

-   **preview** - тестовый режим для 1-5 изображений с выводом ID товаров
-   **scan** - сканирование товаров из product_backup и сохранение в product_images
-   **optimize** - оптимизация изображений через imgproxy (750x1000px, JPEG, 85%)
-   **upload** - загрузка оптимизированных изображений в PIM
-   **full** - полный цикл (scan → optimize → upload)
-   **test** - проверка работы imgproxy

## 🔧 Как это работает

1. **Сканирование**: получает все товары из `product_backup`, извлекает изображения и сохраняет в таблицу `product_images`
2. **Оптимизация**: обрабатывает через imgproxy с параметрами:
    - Ширина: 750px
    - Высота: 1000px (с белым фоном)
    - Формат: JPEG
    - Качество: 85%
3. **Загрузка**: загружает новые изображения в PIM и удаляет старые

## 📊 Таблица product_images

Отслеживает статус каждого изображения:

-   `is_downloaded` - скачано (не используется в текущей версии)
-   `is_optimized` - оптимизировано через imgproxy
-   `is_uploaded` - загружено обратно в PIM

## 🔍 Мониторинг прогресса

```sql
-- Статистика обработки
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN is_optimized THEN 1 ELSE 0 END) as optimized,
    SUM(CASE WHEN is_uploaded THEN 1 ELSE 0 END) as uploaded
FROM product_images;

-- Необработанные изображения
SELECT product_id, image_name, image_type
FROM product_images
WHERE NOT is_optimized
LIMIT 10;
```
