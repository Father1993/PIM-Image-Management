-- =====================================================
-- SQL запросы для проверки загруженных данных
-- =====================================================

-- 1. Сколько каталогов загружено?
SELECT COUNT(*) as total_catalogs FROM catalogs;

-- 2. Корневые каталоги (Уровень-1С, Uroven.pro, Uroven.store)
SELECT 
    id,
    header,
    level,
    product_count,
    enabled,
    (SELECT COUNT(*) FROM catalogs c2 WHERE c2.parent_id = c.id) as children_count
FROM catalogs c
WHERE level = 2
ORDER BY header;

-- 3. Сколько связей товары↔каталоги?
SELECT COUNT(*) as total_links FROM product_catalogs;

-- 4. Товары в "Уровень - 1с" (необработанные из 1С)
SELECT COUNT(DISTINCT pc.product_id) as products_count
FROM product_catalogs pc
JOIN catalogs c ON pc.catalog_id = c.id
WHERE c.header LIKE '%Уровень%1%';

-- 5. Товары в "Uroven.pro" (готовые для сайта)
SELECT COUNT(DISTINCT pc.product_id) as products_count
FROM product_catalogs pc
JOIN catalogs c ON pc.catalog_id = c.id
WHERE c.header = 'Uroven.pro' 
   OR c.parent_id = (SELECT id FROM catalogs WHERE header = 'Uroven.pro');

-- 6. Пример: Категории товара ID=119
SELECT 
    c.id,
    c.header,
    c.path,
    pc.is_primary,
    pc.sort_order
FROM catalogs c
JOIN product_catalogs pc ON c.id = pc.catalog_id
WHERE pc.product_id = 119
ORDER BY pc.is_primary DESC, pc.sort_order;

-- 7. Пример: Товары категории "Электроинструмент"
SELECT 
    p.id,
    p.product_name,
    p.article,
    pc.is_primary
FROM products p
JOIN product_catalogs pc ON p.id = pc.product_id
JOIN catalogs c ON pc.catalog_id = c.id
WHERE c.header LIKE '%Электроинструмент%'
LIMIT 10;

-- 8. Топ-10 категорий по количеству товаров
SELECT 
    c.id,
    c.header,
    c.path,
    COUNT(DISTINCT pc.product_id) as products_count
FROM catalogs c
LEFT JOIN product_catalogs pc ON c.id = pc.catalog_id
GROUP BY c.id, c.header, c.path
ORDER BY products_count DESC
LIMIT 10;

-- 9. Товары без категорий (должно быть мало или 0)
SELECT 
    p.id,
    p.product_name,
    p.article
FROM products p
LEFT JOIN product_catalogs pc ON p.id = pc.product_id
WHERE pc.product_id IS NULL
LIMIT 10;

-- 10. Товары с несколькими категориями
SELECT 
    p.id,
    p.product_name,
    COUNT(pc.catalog_id) as categories_count,
    STRING_AGG(c.header, ', ') as categories
FROM products p
JOIN product_catalogs pc ON p.id = pc.product_id
JOIN catalogs c ON pc.catalog_id = c.id
GROUP BY p.id, p.product_name
HAVING COUNT(pc.catalog_id) > 1
ORDER BY categories_count DESC
LIMIT 10;

-- 11. Структура каталога "Uroven.pro" (первые 2 уровня)
SELECT 
    c.id,
    c.header,
    c.level,
    c.path,
    c.product_count,
    c.last_level
FROM catalogs c
WHERE c.lft > (SELECT lft FROM catalogs WHERE header = 'Uroven.pro')
  AND c.rgt < (SELECT rgt FROM catalogs WHERE header = 'Uroven.pro')
  AND c.level <= 4
ORDER BY c.lft
LIMIT 20;

-- 12. Проверка триггера (счетчик должен совпадать)
SELECT 
    c.id,
    c.header,
    c.product_count as counter_value,
    COUNT(pc.product_id) as actual_count,
    CASE 
        WHEN c.product_count = COUNT(pc.product_id) THEN '✅ OK'
        ELSE '❌ MISMATCH'
    END as status
FROM catalogs c
LEFT JOIN product_catalogs pc ON c.id = pc.catalog_id
GROUP BY c.id, c.header, c.product_count
HAVING c.product_count != COUNT(pc.product_id)
LIMIT 10;

