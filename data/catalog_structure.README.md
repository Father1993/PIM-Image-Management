# Экспорт и работа со структурой каталогов COMPO PIM

Полное руководство по экспорту структуры каталогов из COMPO PIM и загрузке в Supabase для создания собственной админ-панели.

## 📋 Оглавление

1. [Обзор структуры каталога](#обзор-структуры-каталога)
2. [Скрипты экспорта](#скрипты-экспорта)
3. [Структура данных](#структура-данных)
4. [Загрузка в Supabase](#загрузка-в-supabase)
5. [Работа с иерархией](#работа-с-иерархией)
6. [Примеры использования](#примеры-использования)

---

## Обзор структуры каталога

### Архитектура данных в COMPO PIM

COMPO PIM использует **Nested Sets** (вложенные множества) для хранения иерархии каталогов. Это позволяет:

- Быстро получать все потомки каталога
- Эффективно строить пути в дереве
- Проверять принадлежность к ветке
- Подсчитывать товары в ветке

#### Ключевые поля:

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Уникальный идентификатор |
| `header` | String | Название каталога |
| `syncUid` | UUID | Глобальный идентификатор для синхронизации |
| `parentId` | Integer | ID родительского каталога |
| `lft` | Integer | Левая граница (Nested Sets) |
| `rgt` | Integer | Правая граница (Nested Sets) |
| `level` | Integer | Уровень вложенности (1, 2, 3...) |
| `lastLevel` | Boolean | Конечный уровень (может содержать товары) |
| `productCountPim` | Integer | Количество товаров в категории |

### Пример структуры:

```
Электроника (id: 1, lft: 1, rgt: 10, level: 1)
├── Компьютеры (id: 2, lft: 2, rgt: 5, level: 2)
│   ├── Ноутбуки (id: 3, lft: 3, rgt: 4, level: 3, lastLevel: true)
├── Телефоны (id: 4, lft: 6, rgt: 9, level: 2)
│   ├── Смартфоны (id: 5, lft: 7, rgt: 8, level: 3, lastLevel: true)
```

---

## Скрипты экспорта

### 1. `export_catalog_structure.py`

**Назначение:** Экспорт полной структуры каталогов из PIM в JSON.

**Что делает:**
- Получает полное дерево каталогов через API `/api/v1/catalog`
- Рекурсивно обходит дерево и создает плоский список
- Сохраняет метаданные, пути, счетчики
- Строит карту иерархии для быстрого доступа
- Вычисляет статистику

**Использование:**

```bash
# Настройка переменных окружения в .env
PIM_API_URL=https://your-pim.compo-soft.ru
PIM_LOGIN=your_login
PIM_PASSWORD=your_password
PIM_CATALOG_OUTPUT=data/catalog_structure.json

# Запуск
python export/export_catalog_structure.py
```

**Результат:**

Файл `data/catalog_structure.json` со структурой:

```json
{
  "generated_at": "2024-12-22T10:30:00Z",
  "source": "COMPO PIM API",
  "statistics": {
    "total_catalogs": 450,
    "enabled_catalogs": 420,
    "leaf_catalogs": 180,
    "max_depth": 5,
    "total_products": 15000
  },
  "catalogs": [
    {
      "id": 1,
      "header": "Электроника",
      "syncUid": "uuid-here",
      "parentId": null,
      "level": 1,
      "path": "Электроника",
      "pathArray": ["Электроника"],
      "depth": 1,
      "hasChildren": true,
      "childrenCount": 3,
      "lastLevel": false,
      "productCountPim": 5000,
      "lft": 1,
      "rgt": 100
    }
  ],
  "hierarchy_map": {
    "1": {
      "children_ids": [2, 4, 6],
      "parent_id": null
    }
  }
}
```

### 2. `export_product_catalog_links.py`

**Назначение:** Экспорт связей товаров с каталогами.

**Что делает:**
- Получает все товары через scroll API
- Для каждого товара извлекает основной и дополнительные каталоги
- Создает связи `product_id` ↔ `catalog_id`
- Сохраняет информацию о типе связи (основная/дополнительная)

**Использование:**

```bash
# Настройка в .env
PIM_PRODUCT_CATALOG=21  # ID каталога для экспорта
PIM_PRODUCT_CATALOG_OUTPUT=data/product_catalog_links.json
PIM_PRODUCT_CONCURRENCY=50  # Параллельные запросы

# Запуск
python export/export_product_catalog_links.py
```

**Результат:**

```json
{
  "generated_at": "2024-12-22T10:45:00Z",
  "catalog_id": 21,
  "statistics": {
    "total_products": 15000,
    "total_links": 18500,
    "primary_links": 15000,
    "additional_links": 3500,
    "unique_catalogs": 180
  },
  "links": [
    {
      "product_id": 12345,
      "catalog_id": 100,
      "catalog_sync_uid": "uuid",
      "catalog_header": "Ноутбуки",
      "is_primary": true,
      "sort_order": 0
    }
  ],
  "products": [...]
}
```

---

## Структура данных

### Плоский формат каталога

Каждый каталог содержит:

```typescript
interface Catalog {
  // Идентификация
  id: number;
  header: string;
  syncUid: string;
  
  // Иерархия
  parentId: number | null;
  level: number;
  lft: number;
  rgt: number;
  lastLevel: boolean;
  
  // Путь
  path: string;              // "Электроника > Компьютеры > Ноутбуки"
  pathArray: string[];       // ["Электроника", "Компьютеры", "Ноутбуки"]
  depth: number;             // 3
  
  // Дети
  hasChildren: boolean;
  childrenCount: number;
  
  // Товары
  productCount: number;
  productCountPim: number;
  
  // Состояние
  enabled: boolean;
  deleted: boolean;
  pos: number;
  
  // SEO
  htHead: string;
  htDesc: string;
  htKeywords: string;
  content: string;
  
  // Временные метки
  createdAt: string;
  updatedAt: string;
}
```

### Связи товаров с каталогами

```typescript
interface ProductCatalogLink {
  product_id: number;
  catalog_id: number;
  catalog_sync_uid: string;
  catalog_header: string;
  is_primary: boolean;     // Основная категория
  sort_order: number;      // Порядок сортировки
}
```

---

## Загрузка в Supabase

### Шаг 1: Создание таблиц

```bash
# Выполнить SQL скрипт для создания структуры
psql -h your-supabase.supabase.co \
     -U postgres \
     -d postgres \
     -f export/supabase_catalog_schema.sql
```

Или через Supabase Dashboard:
1. Открыть SQL Editor
2. Скопировать содержимое `supabase_catalog_schema.sql`
3. Выполнить

### Шаг 2: Загрузка каталогов

```bash
# Настройка в .env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# Запуск загрузки
python export/load_catalog_to_supabase.py
```

Скрипт спросит:
- Очистить существующие данные? (y/N)

После загрузки проверит:
- Количество загруженных каталогов
- Распределение по уровням
- Активные/конечные каталоги

### Шаг 3: Загрузка связей товаров

```bash
python export/load_product_catalog_links_to_supabase.py
```

Скрипт спросит:
- Очистить существующие связи? (y/N)
- Обновить счетчики товаров? (Y/n)

---

## Работа с иерархией

### Получение всех потомков каталога

```sql
-- Используя Nested Sets (быстрый способ)
SELECT *
FROM catalogs c2
WHERE c2.lft > (SELECT lft FROM catalogs WHERE id = 1)
  AND c2.rgt < (SELECT rgt FROM catalogs WHERE id = 1)
ORDER BY c2.lft;

-- Или через функцию
SELECT * FROM get_catalog_descendants(1);
```

### Получение пути до корня

```sql
-- Рекурсивный CTE
WITH RECURSIVE ancestors AS (
  SELECT id, header, level, parent_id
  FROM catalogs
  WHERE id = 100
  
  UNION ALL
  
  SELECT c.id, c.header, c.level, c.parent_id
  FROM catalogs c
  INNER JOIN ancestors a ON c.id = a.parent_id
)
SELECT * FROM ancestors ORDER BY level;

-- Или через функцию
SELECT * FROM get_catalog_ancestors(100);
```

### Подсчет товаров в ветке

```sql
-- Включая все подкаталоги
SELECT count_products_in_branch(1);

-- Или через JOIN
SELECT COUNT(DISTINCT pc.product_id)
FROM product_catalogs pc
INNER JOIN catalogs c ON pc.catalog_id = c.id
WHERE c.lft >= (SELECT lft FROM catalogs WHERE id = 1)
  AND c.rgt <= (SELECT rgt FROM catalogs WHERE id = 1);
```

### Получение товаров категории

```sql
-- Только из конкретной категории
SELECT p.*
FROM products p
INNER JOIN product_catalogs pc ON p.id = pc.product_id
WHERE pc.catalog_id = 100;

-- Из категории и всех подкатегорий
SELECT DISTINCT p.*
FROM products p
INNER JOIN product_catalogs pc ON p.id = pc.product_id
INNER JOIN catalogs c ON pc.catalog_id = c.id
WHERE c.lft >= (SELECT lft FROM catalogs WHERE id = 100)
  AND c.rgt <= (SELECT rgt FROM catalogs WHERE id = 100);
```

---

## Примеры использования

### Python: Построение дерева каталогов

```python
import json

def build_tree(catalogs: list[dict]) -> dict:
    """Построение дерева из плоского списка."""
    catalog_map = {c["id"]: {**c, "children": []} for c in catalogs}
    root = {"children": []}
    
    for catalog in catalog_map.values():
        parent_id = catalog.get("parentId")
        if parent_id and parent_id in catalog_map:
            catalog_map[parent_id]["children"].append(catalog)
        else:
            root["children"].append(catalog)
    
    return root

# Использование
with open("data/catalog_structure.json") as f:
    data = json.load(f)

tree = build_tree(data["catalogs"])
```

### Python: Поиск по пути

```python
def find_by_path(catalogs: list[dict], path_parts: list[str]) -> dict | None:
    """Поиск каталога по массиву пути."""
    for catalog in catalogs:
        if catalog["pathArray"] == path_parts:
            return catalog
    return None

# Пример
catalog = find_by_path(
    data["catalogs"],
    ["Электроника", "Компьютеры", "Ноутбуки"]
)
```

### JavaScript: Рендер дерева

```javascript
function renderCatalogTree(catalogs, parentId = null, level = 0) {
  return catalogs
    .filter(c => c.parentId === parentId)
    .map(catalog => ({
      ...catalog,
      level,
      children: renderCatalogTree(catalogs, catalog.id, level + 1)
    }));
}

// Использование в React
function CatalogTree({ catalogs }) {
  const tree = renderCatalogTree(catalogs);
  
  return (
    <ul>
      {tree.map(catalog => (
        <li key={catalog.id}>
          {catalog.header}
          {catalog.children.length > 0 && (
            <CatalogTree catalogs={catalog.children} />
          )}
        </li>
      ))}
    </ul>
  );
}
```

### SQL: Представления для админки

```sql
-- Каталоги с breadcrumbs
CREATE VIEW v_catalogs_with_breadcrumbs AS
SELECT 
  c.id,
  c.header,
  c.path,
  array_to_string(c.path_array, ' > ') as breadcrumb,
  c.level,
  c.product_count_pim,
  c.enabled
FROM catalogs c
WHERE c.deleted = FALSE;

-- Популярные каталоги (топ-20 по товарам)
CREATE VIEW v_popular_catalogs AS
SELECT 
  c.id,
  c.header,
  c.path,
  c.product_count_pim,
  c.last_level
FROM catalogs c
WHERE c.enabled = TRUE 
  AND c.deleted = FALSE
  AND c.product_count_pim > 0
ORDER BY c.product_count_pim DESC
LIMIT 20;
```

---

## Автоматизация

### Cron для регулярной синхронизации

```bash
# crontab -e

# Каждый день в 3:00 - обновление каталогов
0 3 * * * cd /path/to/project && python export/export_catalog_structure.py && python export/load_catalog_to_supabase.py

# Каждый день в 4:00 - обновление связей товаров
0 4 * * * cd /path/to/project && python export/export_product_catalog_links.py && python export/load_product_catalog_links_to_supabase.py
```

### Обработка изменений

```python
# Пример инкрементального обновления
def sync_catalog_changes(last_sync: datetime):
    """Синхронизация только измененных каталогов."""
    # Получить каталоги, измененные после last_sync
    catalogs = fetch_updated_catalogs(last_sync)
    
    # Обновить в Supabase
    for catalog in catalogs:
        supabase.table("catalogs").upsert(catalog).execute()
```

---

## Troubleshooting

### Проблема: Ошибка "Foreign key constraint"

**Решение:** Загружайте каталоги в порядке возрастания `level`:

```python
catalogs_sorted = sorted(catalogs, key=lambda x: x["level"])
```

### Проблема: Дублирование связей

**Решение:** Используйте `UPSERT` с правильным конфликтным ключом:

```python
supabase.table("product_catalogs").upsert(
    links,
    on_conflict="product_id,catalog_id"
).execute()
```

### Проблема: Медленные запросы

**Решение:** Проверьте индексы:

```sql
-- Убедитесь, что индексы созданы
\d+ catalogs
\d+ product_catalogs

-- Анализ плана запроса
EXPLAIN ANALYZE
SELECT * FROM catalogs WHERE lft > 10 AND rgt < 100;
```

---

## Следующие шаги

1. ✅ Экспорт структуры каталогов
2. ✅ Создание таблиц в Supabase
3. ✅ Загрузка данных
4. 🔄 Создание API для админ-панели
5. 🔄 Построение UI для управления каталогами
6. 🔄 Реализация drag-and-drop для перемещения
7. 🔄 Синхронизация изменений обратно в PIM

---

## Полезные ссылки

- [Nested Sets в PostgreSQL](https://www.postgresql.org/docs/current/queries-with.html)
- [Supabase Documentation](https://supabase.com/docs)
- [COMPO PIM API](../docs/API-COMPO-PIM.md)

