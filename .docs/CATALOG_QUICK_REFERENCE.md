# ⚡ Быстрая справка: Работа с каталогами

## Команды

```bash
# Экспорт из PIM
python export/export_catalog_structure.py        # Каталоги
python export/export_product_catalog_links.py    # Связи

# Загрузка в Supabase
python export/link_products_to_catalogs.py       # Всё сразу
```

---

## SQL запросы

### Навигация

```sql
-- Корневые каталоги
SELECT * FROM v_root_catalogs;

-- Дети категории
SELECT * FROM catalogs WHERE parent_id = :id;

-- Все потомки
SELECT * FROM get_catalog_descendants(:id);

-- Путь к корню
SELECT * FROM get_catalog_ancestors(:id);
```

### Товары

```sql
-- Товары категории
SELECT p.* FROM products p
JOIN product_catalogs pc ON p.id = pc.product_id
WHERE pc.catalog_id = :catalog_id;

-- Категории товара
SELECT c.*, pc.is_primary FROM catalogs c
JOIN product_catalogs pc ON c.id = pc.catalog_id
WHERE pc.product_id = :product_id;

-- Основная категория товара
SELECT c.* FROM catalogs c
JOIN product_catalogs pc ON c.id = pc.catalog_id
WHERE pc.product_id = :product_id AND pc.is_primary = TRUE;
```

### Управление

```sql
-- Добавить товар в категорию
INSERT INTO product_catalogs (product_id, catalog_id, is_primary)
VALUES (:product_id, :catalog_id, FALSE);

-- Переместить в другую категорию (сменить основную)
UPDATE product_catalogs SET is_primary = FALSE 
WHERE product_id = :id;

UPDATE product_catalogs SET is_primary = TRUE 
WHERE product_id = :id AND catalog_id = :new_catalog_id;

-- Удалить из категории
DELETE FROM product_catalogs 
WHERE product_id = :id AND catalog_id = :catalog_id;
```

### Статистика

```sql
-- Товаров в категории
SELECT COUNT(*) FROM product_catalogs WHERE catalog_id = :id;

-- Товаров в ветке (включая подкатегории)
SELECT COUNT(DISTINCT pc.product_id)
FROM product_catalogs pc
WHERE pc.catalog_id IN (
    SELECT id FROM catalogs WHERE lft >= :lft AND rgt <= :rgt
);

-- Активные категории с товарами
SELECT * FROM v_catalogs_with_products;
```

---

## Структура таблиц

### catalogs

```
id              BIGINT       ID из PIM
header          TEXT         Название
parent_id       BIGINT       Родитель
lft, rgt        INTEGER      Nested Sets
level           INTEGER      Уровень вложенности
path            TEXT         Путь (А > Б > В)
path_array      TEXT[]       Путь массивом
product_count   INTEGER      Счетчик (авто)
enabled         BOOLEAN      Активна?
```

### product_catalogs

```
product_id      BIGINT       products.id
catalog_id      BIGINT       catalogs.id
is_primary      BOOLEAN      Основная?
sort_order      INTEGER      Порядок
```

---

## Индексы

```sql
-- Производительность гарантирована!
idx_catalogs_parent_id         -- Навигация
idx_catalogs_lft_rgt           -- Nested Sets
idx_product_catalogs_product   -- Товары → категории
idx_product_catalogs_catalog   -- Категории → товары
```

---

## Триггер

**Автообновление счетчиков:**  
При добавлении/удалении товара из категории → счетчик `product_count` обновляется автоматически.

---

## Python (Supabase)

```python
from supabase import create_client

supabase = create_client(url, key)

# Товары категории
products = supabase.table("products") \
    .select("*, product_catalogs!inner(catalog_id)") \
    .eq("product_catalogs.catalog_id", catalog_id) \
    .execute()

# Категории товара
catalogs = supabase.table("catalogs") \
    .select("*, product_catalogs!inner(is_primary)") \
    .eq("product_catalogs.product_id", product_id) \
    .execute()

# Добавить в категорию
supabase.table("product_catalogs").insert({
    "product_id": 119,
    "catalog_id": 826,
    "is_primary": False
}).execute()
```

---

## TypeScript (NextJS/Admin)

```typescript
// Дерево каталогов
const { data: catalogs } = await supabase
  .from('catalogs')
  .select('*')
  .eq('parent_id', parentId)
  .order('pos');

// Товары категории
const { data: products } = await supabase
  .from('products')
  .select(`
    *,
    product_catalogs!inner(catalog_id)
  `)
  .eq('product_catalogs.catalog_id', catalogId);

// Breadcrumbs
const { data: path } = await supabase
  .rpc('get_catalog_ancestors', { catalog_id_param: catalogId });
```

---

## Ключевые файлы

```
export/
  ├── supabase_catalog_schema.sql      ← SQL схема
  ├── link_products_to_catalogs.py     ← Загрузка всего
  ├── export_catalog_structure.py      ← Экспорт каталогов
  └── export_product_catalog_links.py  ← Экспорт связей

.docs/
  ├── SETUP_INSTRUCTIONS.md            ← Полная инструкция
  ├── CATALOG_STRUCTURE_DIAGRAM.md     ← Диаграммы
  └── CATALOG_QUICK_REFERENCE.md       ← Эта справка

data/
  ├── catalog_structure.json           ← Каталоги (экспорт)
  └── product_catalog_links.json       ← Связи (экспорт)
```

---

## Важно

1. **ID товара:** `products.id` = `PIM product.id` (прямое соответствие)
2. **Триггер:** Счетчики обновляются автоматически
3. **Upsert:** Безопасно перезапускать `link_products_to_catalogs.py`
4. **Nested Sets:** Быстрые запросы дерева (не делать UPDATE lft/rgt вручную!)

---

🎯 **Всё просто, быстро, понятно!**

