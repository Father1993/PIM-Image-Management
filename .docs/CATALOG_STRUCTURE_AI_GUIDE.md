# 🤖 AI Инструкция: Структура каталогов и связей с товарами

## 📊 Архитектура данных

### Таблицы

```
products (основная таблица товаров)
    ↓
product_catalogs (связующая таблица many-to-many)
    ↓
catalogs (иерархия каталогов через Nested Sets)
```

---

## 1️⃣ Таблица `products`

**НЕ ИЗМЕНЯЕТСЯ!** Остается как есть.

**Ключевое поле для связи:** `code_1c` (артикул товара из 1С)

```sql
-- Структура (важные поля)
products:
  - id (bigint) - внутренний ID в Supabase
  - code_1c (text) - артикул из 1С/PIM (ключ для связи!)
  - product_name (text)
  - description (text)
  - article (text)
  - и другие поля...
```

---

## 2️⃣ Таблица `catalogs` (иерархия категорий)

**Хранит ВСЕ каталоги** (1С, Uroven.pro и т.д.) в одной таблице.

### Важные поля:

```sql
catalogs:
  - id (bigint) - ID категории
  - header (text) - название категории
  - parent_id (bigint) - ID родительской категории
  - level (integer) - уровень вложенности (2,3,4...)
  - lft, rgt (integer) - границы для Nested Sets
  - path (text) - полный путь "Родитель > Категория > Подкатегория"
  - path_array (text[]) - путь массивом ["Родитель", "Категория"]
  - last_level (boolean) - конечная категория (может содержать товары)
  - sync_uid (uuid) - уникальный ID из PIM
```

### Примеры категорий:

```
ID=21: "Uroven.pro" (level=2, parent_id=1)
  ├── ID=826: "Категория 1" (level=3, parent_id=21)
  └── ID=571: "Категория 2" (level=3, parent_id=21)

ID=1: "Каталог 1С" (level=2, parent_id=NULL)
  ├── ID=100: "Перфораторы" (level=3, parent_id=1)
  └── ID=200: "Электроинструмент" (level=3, parent_id=1)
```

---

## 3️⃣ Таблица `product_catalogs` (связи)

**Связь many-to-many** между товарами и категориями.

```sql
product_catalogs:
  - product_id (bigint) - ID товара из products.id
  - catalog_id (bigint) - ID категории из catalogs.id
  - is_primary (boolean) - основная категория товара
  - sort_order (integer) - порядок сортировки
```

### ⭐ Ключевая концепция:

**Один товар может быть в НЕСКОЛЬКИХ категориях:**
- ✅ Одна **основная** категория (`is_primary=true`)
- ✅ Несколько **дополнительных** категорий (`is_primary=false`)

### Пример:

```
Товар: "Перфоратор AEG" (code_1c="15600525")

product_catalogs:
  ├── product_id=12345, catalog_id=1027, is_primary=TRUE  ← Основная (1С)
  ├── product_id=12345, catalog_id=826, is_primary=FALSE  ← Доп. (Uroven.pro)
  └── product_id=12345, catalog_id=571, is_primary=FALSE  ← Доп. (Uroven.pro)
```

**Товар одновременно в:**
- Каталоге 1С (категория 1027)
- Каталоге Uroven.pro (категории 826 и 571)

---

## 🔍 Как найти товары

### 1. Товары конкретной категории

```sql
SELECT p.*
FROM products p
JOIN product_catalogs pc ON p.id = pc.product_id
WHERE pc.catalog_id = 826; -- ID категории
```

### 2. Все категории товара

```sql
SELECT c.*, pc.is_primary
FROM product_catalogs pc
JOIN catalogs c ON pc.catalog_id = c.id
WHERE pc.product_id = 12345
ORDER BY pc.is_primary DESC;
```

### 3. Основная категория товара (для breadcrumbs)

```sql
SELECT c.path
FROM product_catalogs pc
JOIN catalogs c ON pc.catalog_id = c.id
WHERE pc.product_id = 12345 AND pc.is_primary = TRUE;
```

---

## 🌳 Работа с иерархией (Nested Sets)

### Nested Sets - это:
Два числа `lft` и `rgt`, определяющие границы всех потомков.

```
Пример:
Электроника (lft=1, rgt=10)
├── Компьютеры (lft=2, rgt=5)
│   └── Ноутбуки (lft=3, rgt=4)
└── Телефоны (lft=6, rgt=9)
    └── Смартфоны (lft=7, rgt=8)
```

### 1. Все подкатегории (вся ветка)

```sql
-- Все подкатегории каталога Uroven.pro (ID=21)
SELECT *
FROM catalogs
WHERE lft > (SELECT lft FROM catalogs WHERE id = 21)
  AND rgt < (SELECT rgt FROM catalogs WHERE id = 21)
ORDER BY lft;
```

### 2. Прямые дети (1 уровень)

```sql
-- Непосредственные подкатегории
SELECT *
FROM catalogs
WHERE parent_id = 21
ORDER BY pos, header;
```

### 3. Путь до корня (родители)

```sql
-- Хлебные крошки для категории
SELECT path_array FROM catalogs WHERE id = 826;
-- Результат: ["Uroven.pro", "Инструмент", "Электроинструмент"]
```

### 4. Товары в ветке (категория + все подкатегории)

```sql
-- Все товары каталога Uroven.pro и всех подкатегорий
SELECT DISTINCT p.*
FROM products p
JOIN product_catalogs pc ON p.id = pc.product_id
JOIN catalogs c ON pc.catalog_id = c.id
WHERE c.lft >= (SELECT lft FROM catalogs WHERE id = 21)
  AND c.rgt <= (SELECT rgt FROM catalogs WHERE id = 21);
```

---

## 🎯 Типичные операции

### 1. Добавить товар в категорию

```sql
-- Добавить в дополнительную категорию
INSERT INTO product_catalogs (product_id, catalog_id, is_primary, sort_order)
VALUES (12345, 826, FALSE, 1)
ON CONFLICT (product_id, catalog_id) DO NOTHING;
```

### 2. Сменить основную категорию

```sql
-- Убрать старую основную
UPDATE product_catalogs
SET is_primary = FALSE
WHERE product_id = 12345 AND is_primary = TRUE;

-- Установить новую основную
UPDATE product_catalogs
SET is_primary = TRUE
WHERE product_id = 12345 AND catalog_id = 826;
```

### 3. Удалить товар из категории

```sql
DELETE FROM product_catalogs
WHERE product_id = 12345 AND catalog_id = 826;
```

### 4. Найти товары без категорий

```sql
SELECT p.*
FROM products p
LEFT JOIN product_catalogs pc ON p.id = pc.product_id
WHERE pc.catalog_id IS NULL;
```

---

## 📋 Важные правила

### ✅ Правила работы:

1. **Товар ВСЕГДА связан через `product_catalogs`**, не напрямую!
2. **У товара может быть только ОДНА основная категория** (`is_primary=TRUE`)
3. **Товар может быть в любом количестве дополнительных категорий**
4. **Не изменяем таблицу `products`** - только связи через `product_catalogs`
5. **Для breadcrumbs используем основную категорию** (`is_primary=TRUE`)
6. **Товар может быть в разных каталогах** (1С, Uroven.pro, Ozon и т.д.)

### 🚫 Запрещено:

- ❌ Добавлять поле `catalog_id` в таблицу `products`
- ❌ Хранить категории в JSON полях
- ❌ Иметь больше одной основной категории

---

## 🔗 Связь code_1c с PIM

**Важно:** `code_1c` в таблице `products` = `articul` в PIM

```python
# Из PIM приходит:
pim_product = {
    "id": 119,  # ID в PIM
    "articul": "15600525"  # Это и есть code_1c!
}

# В БД ищем:
SELECT id FROM products WHERE code_1c = '15600525'
# Получаем: id=12345

# Создаем связь:
INSERT INTO product_catalogs (product_id, catalog_id, ...)
VALUES (12345, 826, ...)
```

---

## 🎨 Примеры для UI

### Дерево каталогов для меню:

```sql
-- Корневые каталоги
SELECT id, header FROM catalogs 
WHERE parent_id IS NULL 
ORDER BY pos;

-- Подкатегории для раскрытия
SELECT id, header FROM catalogs 
WHERE parent_id = 21 
ORDER BY pos;
```

### Breadcrumbs товара:

```sql
SELECT 
    c.path_array,
    array_to_string(c.path_array, ' > ') as breadcrumb
FROM products p
JOIN product_catalogs pc ON p.id = pc.product_id AND pc.is_primary = TRUE
JOIN catalogs c ON pc.catalog_id = c.id
WHERE p.code_1c = '15600525';
```

### Фильтр по категориям:

```sql
-- Категории верхнего уровня с товарами
SELECT c.id, c.header, COUNT(DISTINCT pc.product_id) as product_count
FROM catalogs c
LEFT JOIN product_catalogs pc ON c.id = pc.catalog_id
WHERE c.level = 2 AND c.enabled = TRUE
GROUP BY c.id, c.header
HAVING COUNT(DISTINCT pc.product_id) > 0
ORDER BY c.header;
```

---

## 🚀 Быстрая справка

| Задача | SQL |
|--------|-----|
| Товары категории | `JOIN product_catalogs ON catalog_id=X` |
| Категории товара | `JOIN product_catalogs ON product_id=X` |
| Основная категория | `... WHERE is_primary=TRUE` |
| Все подкатегории | `WHERE lft > X AND rgt < Y` |
| Прямые дети | `WHERE parent_id=X` |
| Breadcrumbs | `SELECT path_array` |
| Добавить в категорию | `INSERT INTO product_catalogs` |

---

## ✨ Итого

**Простыми словами:**

1. **Товары** хранятся в `products` (ничего не меняем)
2. **Категории** всех каталогов в `catalogs` (одно дерево для всех)
3. **Связи** товары↔категории в `product_catalogs` (многие ко многим)
4. **Товар может быть везде:** в 1С, Uroven.pro, и любых других каталогах
5. **Одна основная** (`is_primary=true`) + любое количество дополнительных
6. **Nested Sets** для быстрых запросов по дереву

**Связь:** `products.code_1c` = `articul` из PIM → создаем записи в `product_catalogs`

---

Готово! Эта структура позволяет гибко управлять товарами в разных каталогах. 🎯

