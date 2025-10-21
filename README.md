# 🖼️ PIM Image Management Suite

A comprehensive set of tools for analyzing, optimizing, and managing product images in PIM systems.

## 📁 Project Structure

The project contains several specialized scripts for various image processing tasks:

### 🔍 Image Analysis

- **`check_proportion.py`** - find products with reference images 750×1000px
- **`check_small_images_ASYNC.py`** - find products with images < 500px
- **`check_big_images_ASYNC.py`** - find products with images > 1500px
- **`check_all_template_size.py`** - find products with images not matching template
- **`images_ASYNC.py`** - find products without images

### ⚙️ Optimization and Management

- **`optimized.py`** - main optimization script via imgproxy
- **`optimize_from_supabase.py`** - optimize images directly from Supabase database
- **`update_perfect_images.py`** - update `is_perfect` field in Supabase
- **`add_pim_url.py`** - add PIM links to Supabase
- **`base_to_json.py`** - export GUID and image_optimized_url from Supabase to JSON
- **`json_to_base.py`** - bulk import GUID data from JSON to Supabase

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables Setup

Create a `.env` file with the required variables:

```env
# PIM API
PIM_API_URL=your_pim_api_url
PIM_LOGIN=your_login
PIM_PASSWORD=your_password
PIM_IMAGE_URL=your_image_url

# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Imgproxy (for optimization)
IMGPROXY_URL=your_imgproxy_url
```

### 3. Create Supabase Table

Execute SQL from the `create_product_images_table.sql` file

## 🔍 Image Analysis

### Find Reference Images (750×1000px)

```bash
python check_proportion.py
```

- Finds products with 750×1000px images
- Saves results to Excel file
- Generates `products_reference_750x1000.xlsx` file

### Find Problematic Images

```bash
# Images smaller than 500px
python check_small_images_ASYNC.py

# Images larger than 1500px
python check_big_images_ASYNC.py

# Images not matching template (500-1500px)
python check_all_template_size.py

# Products without images
python images_ASYNC.py
```

## ⚙️ Image Optimization

### Main Optimization Script

```bash
# Test mode - processes 1-5 images
python optimized.py preview

# Scan all images
python optimized.py scan

# Optimize via imgproxy
python optimized.py optimize

# Upload back to PIM
python optimized.py upload

# Full cycle (scan → optimize → upload)
python optimized.py full

# Test imgproxy functionality
python optimized.py test
```

### Optimize from Supabase

```bash
# Optimize all unprocessed products
python optimize_from_supabase.py

# Optimize with limit (e.g., 100 products)
python optimize_from_supabase.py 100
```

Скрипт автоматически:

- Получает продукты с неоптимизированными изображениями из Supabase
- Оптимизирует через imgproxy (750×1000px, белый фон)
- Загружает в бакет `optimized` с структурой по датам (год/месяц/день)
- Обновляет поля `is_optimized`, `optimized_url` в базе
- Обрабатывает батчами по 100 продуктов параллельно

### Database Updates

```bash
# Update is_perfect field for reference images
python update_perfect_images.py

# Add PIM links to Supabase
python add_pim_url.py

# Export GUID data to export.json
python base_to_json.py

# Import GUID data from products.json
python json_to_base.py
```

### Upload Optimized Images to PIM

```bash
# Upload optimized images back to PIM system
python push_optimized_images_to_pim.py
```

Скрипт автоматически:

- Получает товары с оптимизированными изображениями из Supabase
- Скачивает изображения по URL из поля `image_optimized_url`
- Загружает изображения в PIM через API `/api/v1/product/{id}/upload-main-picture`
- Обрабатывает батчами по 1000 товаров параллельно (макс. 100 одновременно)
- Сохраняет прогресс в `upload_progress.json` для возможности возобновления
- Поддерживает корректную остановку (Ctrl+C) с сохранением прогресса

**base_to_json.py** - экспортирует code_1c, GUID и image_optimized_url из Supabase в JSON:

- Выгружает все записи с заполненным GUID из базы
- Сохраняет в `export.json` массив объектов `{code_1c, GUID, image_optimized_url}`
- Использует cursor-based пагинацию для надежности
- Автоматически удаляет дубликаты по GUID

**json_to_base.py** - импортирует GUID из JSON файла в Supabase:

- Читает `products.json` с массивом объектов `{code_1c, GUID}`
- Обновляет поле GUID по совпадению code_1c
- Обрабатывает батчами по 250, параллельно по 30 запросов
- Показывает прогресс по батчам

## 📊 Optimization Parameters

All images are optimized with the following parameters:

- **Width**: 750px
- **Height**: 1000px (with white background)
- **Format**: JPEG
- **Quality**: 85%

## 📋 product_images Table

Tracks the status of each image:

| Field          | Description                  |
| -------------- | ---------------------------- |
| `id`           | Unique record ID             |
| `product_id`   | Product ID in PIM            |
| `image_name`   | Image file name              |
| `image_type`   | Image type (Main/Additional) |
| `is_optimized` | Optimized via imgproxy       |
| `is_uploaded`  | Uploaded back to PIM         |
| `is_perfect`   | Reference image 750×1000px   |

## 🔍 Progress Monitoring

```sql
-- General statistics
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN is_optimized THEN 1 ELSE 0 END) as optimized,
    SUM(CASE WHEN is_uploaded THEN 1 ELSE 0 END) as uploaded,
    SUM(CASE WHEN is_perfect THEN 1 ELSE 0 END) as perfect
FROM product_images;

-- Unprocessed images
SELECT product_id, image_name, image_type
FROM product_images
WHERE NOT is_optimized
LIMIT 10;

-- Reference images
SELECT product_id, image_name, image_type
FROM product_images
WHERE is_perfect = true
LIMIT 10;
```

## 📁 Output Files

Scripts generate Excel files with analysis results:

- `products_reference_750x1000_ASYNC_[date].xlsx` - products with reference images
- `products_small_images_ASYNC_[date].xlsx` - products with small images
- `products_big_images_ASYNC_[date].xlsx` - products with large images
- `products_no_template_size_ASYNC_[date].xlsx` - products with unsuitable images
- `products_without_images_ASYNC_[date].xlsx` - products without images

Database export/import files:

- `export.json` - exported code_1c, GUID and image_optimized_url from Supabase
- `products.json` - GUID data for import to Supabase

Progress tracking files:

- `upload_progress.json` - progress tracking for push_optimized_images_to_pim.py

## 🛠️ Technical Features

- **Asynchronous Processing** - all scripts use asyncio for fast operation
- **Batch Processing** - data is processed in batches to avoid API overload
- **Caching** - image sizes are cached to speed up repeated checks
- **Error Handling** - all scripts are resilient to network errors and timeouts
- **Progress Indicators** - detailed information about execution progress
- **Progress Persistence** - push_optimized_images_to_pim.py saves progress to resume interrupted uploads
- **Token Management** - automatic PIM API token refresh to prevent authentication failures
- **Graceful Shutdown** - supports Ctrl+C with progress preservation

## 📝 Logging

All scripts maintain detailed logs in the `image_optimizer.log` file with information about:

- Operation execution time
- Number of processed products
- Errors and warnings
- Result statistics
