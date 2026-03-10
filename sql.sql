-- ============================================================================
-- CLEANUP
-- ============================================================================
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS stores CASCADE;
DROP TABLE IF EXISTS products CASCADE;

-- ============================================================================
-- PRODUCTS TABLE - Master product catalog with PSKU-SKU hierarchy
-- ============================================================================
CREATE TABLE products (
    product_id BIGINT PRIMARY KEY,
    category TEXT NOT NULL CHECK (category IN ('Food & Beverages','Personal Care','Home Care','Snacks','Baby & Childcare','Health')),
    sub_category TEXT NOT NULL,
    brand TEXT NOT NULL,
    sub_brand TEXT,
    psku TEXT NOT NULL,
    psku_code TEXT NOT NULL,
    sku TEXT NOT NULL,
    sku_code TEXT UNIQUE NOT NULL,
    weight_value NUMERIC,
    weight_unit TEXT,
    count_value NUMERIC,
    unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price > 0),
    created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_timestamp TIMESTAMP
);

COMMENT ON TABLE products IS 'Master product catalog containing ~100K-125K SKUs organized into ~5K PSKUs';
COMMENT ON COLUMN products.psku IS 'Parent SKU representing product family for brand management';
COMMENT ON COLUMN products.sku IS 'Individual SKU representing tactical sellable unit with specific pack size';
COMMENT ON COLUMN products.psku_code IS 'Unique identifier formatted as {BRAND}_{CATEGORY}_{SUBCATEGORY}_{SEQ}';
COMMENT ON COLUMN products.sku_code IS 'Unique identifier formatted as {PSKU_CODE}_VAR_{WEIGHT}{UNIT}_{SEQ}';

-- ============================================================================
-- STORES TABLE - Retail network topology
-- ============================================================================
CREATE TABLE stores (
    store_id INT PRIMARY KEY,
    store_type TEXT NOT NULL CHECK (store_type IN ('Hypermarket','Supermarket','Large','Medium','Small','Mobile')),
    cycle_days INT NOT NULL CHECK (cycle_days IN (5,6,7)),
    avg_sales_multiplier NUMERIC(4,2) NOT NULL CHECK (avg_sales_multiplier > 0 AND avg_sales_multiplier <= 2.5),
    city TEXT,
    region TEXT,
    state TEXT,
    pin_code INT,
    area_type TEXT,
    established_date DATE
);

COMMENT ON TABLE stores IS 'Retail network spanning Hypermarkets to Mobile vendors with 1,500-5,000 stores';
COMMENT ON COLUMN stores.cycle_days IS 'Replenishment cycle frequency: 7=Hypermarket/Mobile, 6=Supermarket, 5=Large/Medium/Small';
COMMENT ON COLUMN stores.avg_sales_multiplier IS 'Relative sales volume: 2.0=Hypermarket, 1.5=Supermarket, 1.0=Large, 0.8=Medium, 0.6=Small, 0.4=Mobile';

-- ============================================================================
-- ORDERS TABLE - Primary fact table with ~1 billion records
-- ============================================================================
CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    store_id INT NOT NULL REFERENCES stores(store_id),
    product_id BIGINT NOT NULL,
    order_date DATE NOT NULL CHECK (order_date BETWEEN '2023-06-01' AND '2025-12-31'),
    quantity INT NOT NULL CHECK (quantity >= 1),
    total_value NUMERIC(12,2) NOT NULL CHECK (total_value > 0),
    created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE orders IS 'Approximately 1 billion order records spanning June 2023 to December 2025';
COMMENT ON COLUMN orders.quantity IS 'Units ordered - follows Poisson distribution scaled by store sales multiplier';
COMMENT ON COLUMN orders.total_value IS 'Order value in INR including realistic price variance';

-- ============================================================================
-- TRANSACTIONS TABLE - 1:1 correspondence with orders
-- ============================================================================
CREATE TABLE transactions (
    transaction_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id),
    store_id INT NOT NULL,
    product_id BIGINT NOT NULL,
    date DATE NOT NULL CHECK (date BETWEEN '2023-06-01' AND '2025-12-31'),
    quantity INT NOT NULL CHECK (quantity >= 1),
    value NUMERIC(12,2) NOT NULL CHECK (value > 0),
    unit_price NUMERIC(10,2)
);

COMMENT ON TABLE transactions IS 'Transaction records with perfect 1:1 correspondence to orders table';

-- ============================================================================
-- PERFORMANCE INDEXES
-- ============================================================================
-- Critical indexes for query performance
CREATE INDEX idx_products_psku ON products(psku_code);
CREATE INDEX idx_products_category_brand ON products(category, brand);
CREATE INDEX idx_products_sku ON products(sku_code);
CREATE INDEX idx_products_brand ON products(brand);

CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_store ON orders(store_id);
CREATE INDEX idx_orders_product ON orders(product_id);
CREATE INDEX idx_orders_store_date ON orders(store_id, order_date);

CREATE INDEX idx_transactions_order ON transactions(order_id);
CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_store_date ON transactions(store_id, date);

-- ============================================================================
-- BULK LOADING OPTIMIZATION
-- ============================================================================
-- For bulk loading 1 billion orders, drop indexes before INSERT and recreate after
-- This improves insertion throughput from ~2,000 to ~20,000 orders/second

-- Before bulk load:
-- DROP INDEX IF EXISTS idx_orders_date;
-- DROP INDEX IF EXISTS idx_orders_store;
-- DROP INDEX IF EXISTS idx_orders_product;
-- DROP INDEX IF EXISTS idx_orders_store_date;

-- After bulk load:
-- CREATE INDEX idx_orders_date ON orders(order_date);
-- CREATE INDEX idx_orders_store ON orders(store_id);
-- CREATE INDEX idx_orders_product ON orders(product_id);
-- CREATE INDEX idx_orders_store_date ON orders(store_id, order_date);

-- ============================================================================
-- CSV LOADING COMMANDS
-- ============================================================================
-- Load data from CSV files (update paths as needed)
-- COPY products FROM '/path/to/product.csv' DELIMITER ',' CSV HEADER;
-- COPY stores FROM '/path/to/store.csv' DELIMITER ',' CSV HEADER;
-- COPY transactions FROM '/path/to/transaction.csv' DELIMITER ',' CSV HEADER;

-- ============================================================================
-- POSTGRESQL CONFIGURATION FOR OPTIMAL BULK LOAD
-- ============================================================================
-- Recommended postgresql.conf settings for bulk loading:
-- shared_buffers = 8GB
-- work_mem = 256MB
-- maintenance_work_mem = 2GB
-- effective_cache_size = 24GB
-- checkpoint_completion_target = 0.9
-- max_wal_size = 4GB
-- synchronous_commit = off  (during load only - re-enable after)
-- max_connections = 100
-- random_page_cost = 1.1  (for SSD storage)

-- ============================================================================
-- POST-LOAD MAINTENANCE
-- ============================================================================
-- After bulk loading, update table statistics for query optimizer
-- VACUUM ANALYZE products;
-- VACUUM ANALYZE stores;
-- VACUUM ANALYZE orders;
-- VACUUM ANALYZE transactions;

-- Check table sizes
-- SELECT 
--   schemaname,
--   tablename,
--   pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
-- FROM pg_tables 
-- WHERE schemaname = 'public'
-- ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;