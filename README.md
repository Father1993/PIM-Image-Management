# 🖼️ PIM Image Management Suite

Комплексный набор инструментов для анализа, оптимизации и управления изображениями товаров в PIM системе.

## 📁 Структура проекта

Проект содержит несколько специализированных скриптов для различных задач работы с изображениями:

### 🔍 Анализ изображений

-   **`check_proportion.py`** - поиск товаров с эталонными изображениями 750×1000px
-   **`check_small_images_ASYNC.py`** - поиск товаров с изображениями < 500px
-   **`check_big_images_ASYNC.py`** - поиск товаров с изображениями > 1500px
-   **`check_all_template_size.py`** - поиск товаров с изображениями не соответствующими шаблону
-   **`images_ASYNC.py`** - поиск товаров без изображений

### ⚙️ Оптимизация и управление

-   **`optimized.py`** - основной скрипт оптимизации через imgproxy
-   **`update_perfect_images.py`** - обновление поля `is_perfect` в Supabase
-   **`add_pim_url.py`** - добавление ссылок PIM в Supabase

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

Создайте файл `.env` с необходимыми переменными:

```env
# PIM API
PIM_API_URL=your_pim_api_url
PIM_LOGIN=your_login
PIM_PASSWORD=your_password
PIM_IMAGE_URL=your_image_url

# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Imgproxy (для оптимизации)
IMGPROXY_URL=your_imgproxy_url
```

### 3. Создайте таблицу в Supabase

Выполните SQL из файла `create_product_images_table.sql`

## 🔍 Анализ изображений

### Поиск эталонных изображений (750×1000px)

```bash
python check_proportion.py
```

-   Находит товары с изображениями размером 750×1000px
-   Сохраняет результат в Excel файл
-   Генерирует файл `products_reference_750x1000.xlsx`

### Поиск проблемных изображений

```bash
# Изображения меньше 500px
python check_small_images_ASYNC.py

# Изображения больше 1500px
python check_big_images_ASYNC.py

# Изображения не соответствующие шаблону (500-1500px)
python check_all_template_size.py

# Товары без изображений
python images_ASYNC.py
```

## ⚙️ Оптимизация изображений

### Основной скрипт оптимизации

```bash
# Тестовый режим - обработает 1-5 изображений
python optimized.py preview

# Сканирование всех изображений
python optimized.py scan

# Оптимизация через imgproxy
python optimized.py optimize

# Загрузка обратно в PIM
python optimized.py upload

# Полный цикл (scan → optimize → upload)
python optimized.py full

# Проверка работы imgproxy
python optimized.py test
```

### Обновление базы данных

```bash
# Обновление поля is_perfect для эталонных изображений
python update_perfect_images.py

# Добавление ссылок PIM в Supabase
python add_pim_url.py
```

## 📊 Параметры оптимизации

Все изображения оптимизируются с параметрами:

-   **Ширина**: 750px
-   **Высота**: 1000px (с белым фоном)
-   **Формат**: JPEG
-   **Качество**: 85%

## 📋 Таблица product_images

Отслеживает статус каждого изображения:

| Поле           | Описание                         |
| -------------- | -------------------------------- |
| `id`           | Уникальный ID записи             |
| `product_id`   | ID товара в PIM                  |
| `image_name`   | Имя файла изображения            |
| `image_type`   | Тип изображения (Основное/Доп.)  |
| `is_optimized` | Оптимизировано через imgproxy    |
| `is_uploaded`  | Загружено обратно в PIM          |
| `is_perfect`   | Эталонное изображение 750×1000px |

## 🔍 Мониторинг прогресса

```sql
-- Общая статистика
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN is_optimized THEN 1 ELSE 0 END) as optimized,
    SUM(CASE WHEN is_uploaded THEN 1 ELSE 0 END) as uploaded,
    SUM(CASE WHEN is_perfect THEN 1 ELSE 0 END) as perfect
FROM product_images;

-- Необработанные изображения
SELECT product_id, image_name, image_type
FROM product_images
WHERE NOT is_optimized
LIMIT 10;

-- Эталонные изображения
SELECT product_id, image_name, image_type
FROM product_images
WHERE is_perfect = true
LIMIT 10;
```

## 📁 Выходные файлы

Скрипты генерируют Excel файлы с результатами анализа:

-   `products_reference_750x1000_ASYNC_[дата].xlsx` - товары с эталонными изображениями
-   `products_small_images_ASYNC_[дата].xlsx` - товары с маленькими изображениями
-   `products_big_images_ASYNC_[дата].xlsx` - товары с большими изображениями
-   `products_no_template_size_ASYNC_[дата].xlsx` - товары с неподходящими изображениями
-   `products_without_images_ASYNC_[дата].xlsx` - товары без изображений

## 🛠️ Технические особенности

-   **Асинхронная обработка** - все скрипты используют asyncio для быстрой работы
-   **Пакетная обработка** - данные обрабатываются пакетами для избежания перегрузки API
-   **Кэширование** - размеры изображений кэшируются для ускорения повторных проверок
-   **Обработка ошибок** - все скрипты устойчивы к сетевым ошибкам и таймаутам
-   **Прогресс-индикаторы** - подробная информация о ходе выполнения

## 📝 Логирование

Все скрипты ведут подробные логи в файл `image_optimizer.log` с информацией о:

-   Времени выполнения операций
-   Количестве обработанных товаров
-   Ошибках и предупреждениях
-   Статистике результатов
