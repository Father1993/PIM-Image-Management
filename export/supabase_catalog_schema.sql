-- =====================================================
-- Схема каталогов для COMPO PIM
-- =====================================================

-- 1. Таблица каталогов (иерархия через Nested Sets)
CREATE TABLE IF NOT EXISTS catalogs (
    id BIGINT PRIMARY KEY,
    header TEXT NOT NULL,
    sync_uid UUID UNIQUE NOT NULL,
    parent_id BIGINT REFERENCES catalogs(id) ON DELETE SET NULL,
    
    -- Nested Sets для быстрых запросов дерева
    lft INTEGER NOT NULL,
    rgt INTEGER NOT NULL,
    level INTEGER NOT NULL DEFAULT 1,
    last_level BOOLEAN DEFAULT FALSE,
    
    -- Путь
    path TEXT,
    path_array TEXT[],
    depth INTEGER DEFAULT 1,
    
    -- Состояние
    pos INTEGER,
    enabled BOOLEAN DEFAULT TRUE,
    deleted BOOLEAN DEFAULT FALSE,
    
    -- Счетчики
    product_count INTEGER DEFAULT 0,
    product_count_pim INTEGER DEFAULT 0,
    
    -- SEO
    ht_head TEXT,
    ht_desc TEXT,
    ht_keywords TEXT,
    content TEXT,
    
    -- Временные метки
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Метаданные (каналы, картинки и т.д.)
    metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT catalogs_nested_sets_check CHECK (lft < rgt)
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_catalogs_parent_id ON catalogs(parent_id);
CREATE INDEX IF NOT EXISTS idx_catalogs_sync_uid ON catalogs(sync_uid);
CREATE INDEX IF NOT EXISTS idx_catalogs_lft_rgt ON catalogs(lft, rgt);
CREATE INDEX IF NOT EXISTS idx_catalogs_level ON catalogs(level);
CREATE INDEX IF NOT EXISTS idx_catalogs_enabled ON catalogs(enabled) WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_catalogs_path ON catalogs USING GIN(path_array);

COMMENT ON TABLE catalogs IS 'Иерархия каталогов (1С, Uroven.pro и т.д.)';


-- 2. Связи товаров с каталогами (many-to-many)
CREATE TABLE IF NOT EXISTS product_catalogs (
    product_id BIGINT NOT NULL,  -- ID из products.id = PIM product.id
    catalog_id BIGINT NOT NULL REFERENCES catalogs(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (product_id, catalog_id)
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_product_catalogs_product_id ON product_catalogs(product_id);
CREATE INDEX IF NOT EXISTS idx_product_catalogs_catalog_id ON product_catalogs(catalog_id);
CREATE INDEX IF NOT EXISTS idx_product_catalogs_primary ON product_catalogs(is_primary) WHERE is_primary = TRUE;

COMMENT ON TABLE product_catalogs IS 'Связь товары ↔ каталоги (products.id = PIM id)';
COMMENT ON COLUMN product_catalogs.product_id IS 'ID товара из products.id (совпадает с PIM ID)';


-- 3. Функции для работы с иерархией

-- Получить все подкатегории
CREATE OR REPLACE FUNCTION get_catalog_descendants(catalog_id_param BIGINT)
RETURNS TABLE (id BIGINT, header TEXT, level INTEGER, path TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT c.id, c.header, c.level, c.path
    FROM catalogs c
    WHERE c.lft > (SELECT lft FROM catalogs WHERE id = catalog_id_param)
      AND c.rgt < (SELECT rgt FROM catalogs WHERE id = catalog_id_param)
    ORDER BY c.lft;
END;
$$ LANGUAGE plpgsql;

-- Получить путь до корня
CREATE OR REPLACE FUNCTION get_catalog_ancestors(catalog_id_param BIGINT)
RETURNS TABLE (id BIGINT, header TEXT, level INTEGER) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE ancestors AS (
        SELECT c.id, c.header, c.level, c.parent_id
        FROM catalogs c
        WHERE c.id = catalog_id_param
        
        UNION ALL
        
        SELECT c.id, c.header, c.level, c.parent_id
        FROM catalogs c
        INNER JOIN ancestors a ON c.id = a.parent_id
    )
    SELECT a.id, a.header, a.level
    FROM ancestors a
    ORDER BY a.level;
END;
$$ LANGUAGE plpgsql;

-- Триггер: автообновление счетчика товаров
CREATE OR REPLACE FUNCTION update_catalog_product_counts()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        UPDATE catalogs
        SET product_count = (
            SELECT COUNT(*) FROM product_catalogs WHERE catalog_id = NEW.catalog_id
        )
        WHERE id = NEW.catalog_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE catalogs
        SET product_count = (
            SELECT COUNT(*) FROM product_catalogs WHERE catalog_id = OLD.catalog_id
        )
        WHERE id = OLD.catalog_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_catalog_counts ON product_catalogs;
CREATE TRIGGER trigger_update_catalog_counts
AFTER INSERT OR UPDATE OR DELETE ON product_catalogs
FOR EACH ROW EXECUTE FUNCTION update_catalog_product_counts();


-- 4. Представления

-- Активные каталоги с товарами
CREATE OR REPLACE VIEW v_catalogs_with_products AS
SELECT 
    c.id,
    c.header,
    c.path,
    c.level,
    c.last_level,
    c.product_count,
    c.enabled
FROM catalogs c
WHERE c.enabled = TRUE 
  AND c.deleted = FALSE
  AND c.product_count > 0
ORDER BY c.path;

-- Корневые каталоги (Уровень-1С, Uroven.pro и т.д.)
CREATE OR REPLACE VIEW v_root_catalogs AS
SELECT 
    c.id,
    c.header,
    c.product_count,
    c.enabled,
    (SELECT COUNT(*) FROM catalogs WHERE parent_id = c.id) as children_count
FROM catalogs c
WHERE c.parent_id IS NULL OR c.level = 2
ORDER BY c.header;

COMMENT ON VIEW v_catalogs_with_products IS 'Активные каталоги содержащие товары';
COMMENT ON VIEW v_root_catalogs IS 'Корневые каталоги (Уровень-1С, Uroven.pro)';

