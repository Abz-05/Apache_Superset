-- FMCG Synthetic Data - Comprehensive Analysis Queries
-- Business Intelligence queries for enterprise-scale FMCG retail analytics
-- Date: 2026-01-27

-- ============================================================================
-- Q1: Total Sales by Store Type
-- Purpose: Analyze sales performance across retail formats
-- ============================================================================
SELECT 
    s.store_type,
    s.cycle_days,
    s.avg_sales_multiplier,
    COUNT(o.order_id) as total_orders,
    SUM(o.total_value) as total_revenue,
    AVG(o.total_value) as avg_order_value,
    SUM(o.quantity) as total_units,
    MIN(o.total_value) as min_order_value,
    MAX(o.total_value) as max_order_value,
    STDDEV(o.total_value) as stddev_order_value
FROM orders o
JOIN stores s ON o.store_id = s.store_id
GROUP BY s.store_type, s.cycle_days, s.avg_sales_multiplier
ORDER BY total_revenue DESC;

-- ============================================================================
-- Q2: Top 100 SKUs by Revenue
-- Purpose: Identify best-performing products
-- ============================================================================
SELECT 
    p.sku,
    p.sku_code,
    p.brand,
    p.sub_brand,
    p.category,
    p.sub_category,
    p.psku,
    p.unit_price,
    SUM(o.total_value) as revenue,
    SUM(o.quantity) as units_sold,
    COUNT(o.order_id) as order_count,
    AVG(o.total_value) as avg_order_value,
    COUNT(DISTINCT o.store_id) as store_penetration
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY p.sku, p.sku_code, p.brand, p.sub_brand, p.category, p.sub_category, p.psku, p.unit_price
ORDER BY revenue DESC
LIMIT 100;

-- ============================================================================
-- Q3: Monthly Sales Trend
-- Purpose: Track sales performance over time
-- ============================================================================
SELECT 
    DATE_TRUNC('month', order_date) as month,
    COUNT(order_id) as orders,
    SUM(total_value) as revenue,
    AVG(total_value) as avg_order_value,
    SUM(quantity) as units,
    COUNT(DISTINCT store_id) as active_stores,
    COUNT(DISTINCT product_id) as unique_products
FROM orders
GROUP BY month
ORDER BY month;

-- ============================================================================
-- Q4: Average Order Value by Store Type and Category
-- Purpose: Understand purchasing patterns across formats and categories
-- ============================================================================
SELECT 
    s.store_type,
    p.category,
    COUNT(o.order_id) as order_count,
    AVG(o.total_value) as avg_order_value,
    SUM(o.total_value) as total_revenue,
    SUM(o.quantity) as total_units,
    STDDEV(o.total_value) as stddev_order_value
FROM orders o
JOIN stores s ON o.store_id = s.store_id
JOIN products p ON o.product_id = p.product_id
GROUP BY s.store_type, p.category
ORDER BY s.store_type, avg_order_value DESC;

-- ============================================================================
-- Q5: PSKU-Level Aggregation (Product Family Performance)
-- Purpose: Roll up SKU sales to parent product families
-- ============================================================================
SELECT 
    p.psku,
    p.psku_code,
    p.category,
    p.brand,
    p.sub_brand,
    COUNT(DISTINCT p.sku_code) as sku_count,
    SUM(o.quantity) as total_quantity,
    SUM(o.total_value) as total_revenue,
    AVG(o.total_value) as avg_order_value,
    COUNT(o.order_id) as order_count,
    COUNT(DISTINCT o.store_id) as store_penetration,
    MIN(p.unit_price) as min_sku_price,
    MAX(p.unit_price) as max_sku_price
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY p.psku, p.psku_code, p.category, p.brand, p.sub_brand
ORDER BY total_revenue DESC
LIMIT 200;

-- ============================================================================
-- Q6: Brand Performance Across Categories
-- Purpose: Analyze brand strength in different categories
-- ============================================================================
SELECT 
    p.brand,
    p.category,
    COUNT(DISTINCT p.psku_code) as psku_count,
    COUNT(DISTINCT p.sku_code) as sku_count,
    SUM(o.total_value) as revenue,
    SUM(o.quantity) as units,
    COUNT(o.order_id) as orders,
    AVG(o.total_value) as avg_order_value,
    COUNT(DISTINCT o.store_id) as store_reach
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY p.brand, p.category
ORDER BY revenue DESC;

-- ============================================================================
-- Q7: CRITICAL - Mobile vs Supermarket vs Hypermarket Comparison
-- Purpose: Validate sales multiplier effects and pricing dynamics
-- ============================================================================
SELECT 
    s.store_type,
    s.cycle_days,
    s.avg_sales_multiplier,
    COUNT(DISTINCT s.store_id) as store_count,
    COUNT(o.order_id) as total_orders,
    AVG(o.total_value) as avg_order_value,
    STDDEV(o.total_value) as stddev_order_value,
    SUM(o.total_value) as total_revenue,
    SUM(o.quantity) as total_units,
    MIN(o.total_value) as min_order,
    MAX(o.total_value) as max_order,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY o.total_value) as p25_order_value,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY o.total_value) as median_order_value,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY o.total_value) as p75_order_value
FROM orders o
JOIN stores s ON o.store_id = s.store_id
WHERE s.store_type IN ('Mobile', 'Supermarket', 'Hypermarket')
GROUP BY s.store_type, s.cycle_days, s.avg_sales_multiplier
ORDER BY total_revenue DESC;

-- ============================================================================
-- Q8: Quarterly Sales Analysis
-- Purpose: Track seasonal trends and year-over-year growth
-- ============================================================================
SELECT 
    EXTRACT(YEAR FROM order_date) as year,
    EXTRACT(QUARTER FROM order_date) as quarter,
    COUNT(order_id) as orders,
    SUM(total_value) as revenue,
    AVG(total_value) as avg_order_value,
    SUM(quantity) as units,
    COUNT(DISTINCT store_id) as active_stores,
    COUNT(DISTINCT product_id) as products_sold
FROM orders
GROUP BY year, quarter
ORDER BY year, quarter;

-- ============================================================================
-- Q9: Category Penetration by Store Type
-- Purpose: Understand category mix across retail formats
-- ============================================================================
SELECT 
    s.store_type,
    p.category,
    COUNT(DISTINCT p.product_id) as unique_products,
    COUNT(DISTINCT p.psku_code) as unique_pskus,
    SUM(o.quantity) as units_sold,
    SUM(o.total_value) as revenue,
    COUNT(o.order_id) as orders,
    AVG(o.total_value) as avg_order_value,
    ROUND(100.0 * SUM(o.total_value) / SUM(SUM(o.total_value)) OVER (PARTITION BY s.store_type), 2) as category_share_pct
FROM orders o
JOIN stores s ON o.store_id = s.store_id
JOIN products p ON o.product_id = p.product_id
GROUP BY s.store_type, p.category
ORDER BY s.store_type, revenue DESC;

-- ============================================================================
-- Q10: Market Share by Brand Within Category
-- Purpose: Calculate competitive positioning
-- ============================================================================
SELECT 
    category,
    brand,
    SUM(total_value) as revenue,
    COUNT(order_id) as orders,
    SUM(quantity) as units,
    ROUND(100.0 * SUM(total_value) / SUM(SUM(total_value)) OVER (PARTITION BY category), 2) as category_market_share_pct,
    RANK() OVER (PARTITION BY category ORDER BY SUM(total_value) DESC) as rank_in_category
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY category, brand
ORDER BY category, revenue DESC;

-- ============================================================================
-- Q11: Daily Order Volume Distribution
-- Purpose: Analyze cycle patterns and day-of-week effects
-- ============================================================================
SELECT 
    order_date,
    EXTRACT(DOW FROM order_date) as day_of_week,
    TO_CHAR(order_date, 'Day') as day_name,
    COUNT(order_id) as daily_orders,
    SUM(total_value) as daily_revenue,
    AVG(total_value) as avg_order_value,
    COUNT(DISTINCT store_id) as stores_ordering,
    COUNT(DISTINCT product_id) as products_ordered
FROM orders
GROUP BY order_date
ORDER BY order_date;

-- ============================================================================
-- Q12: PSKU Hierarchy Validation with Pricing
-- Purpose: Verify product family structure and price ranges
-- ============================================================================
SELECT 
    psku,
    psku_code,
    category,
    brand,
    sub_brand,
    COUNT(DISTINCT sku_code) as sku_variants,
    MIN(unit_price) as min_price,
    MAX(unit_price) as max_price,
    AVG(unit_price) as avg_price,
    ROUND(MAX(unit_price)::numeric / NULLIF(MIN(unit_price), 0), 2) as price_range_ratio,
    MIN(weight_value) as min_weight,
    MAX(weight_value) as max_weight,
    STRING_AGG(DISTINCT weight_unit, ', ') as units_used
FROM products
GROUP BY psku, psku_code, category, brand, sub_brand
HAVING COUNT(DISTINCT sku_code) >= 5
ORDER BY sku_variants DESC
LIMIT 200;

-- ============================================================================
-- Q13: Store Performance Ranking
-- Purpose: Identify top and bottom performing stores
-- ============================================================================
SELECT 
    s.store_id,
    s.store_type,
    s.city,
    s.region,
    s.state,
    s.avg_sales_multiplier,
    COUNT(o.order_id) as total_orders,
    SUM(o.total_value) as total_revenue,
    AVG(o.total_value) as avg_order_value,
    SUM(o.quantity) as total_units,
    COUNT(DISTINCT o.product_id) as unique_products_ordered,
    RANK() OVER (PARTITION BY s.store_type ORDER BY SUM(o.total_value) DESC) as rank_within_type,
    ROUND(PERCENT_RANK() OVER (PARTITION BY s.store_type ORDER BY SUM(o.total_value))::numeric * 100, 2) as percentile_within_type
FROM orders o
JOIN stores s ON o.store_id = s.store_id
GROUP BY s.store_id, s.store_type, s.city, s.region, s.state, s.avg_sales_multiplier
ORDER BY total_revenue DESC
LIMIT 500;

-- ============================================================================
-- Q14: Product Velocity Analysis (Fast vs Slow Movers)
-- Purpose: Identify high-frequency and low-frequency products
-- ============================================================================
WITH product_orders AS (
    SELECT 
        p.product_id,
        p.category,
        p.brand,
        p.psku,
        p.sku,
        o.order_date,
        o.order_id,
        o.quantity,
        o.total_value,
        LAG(o.order_date) OVER (PARTITION BY p.product_id ORDER BY o.order_date) as prev_order_date
    FROM orders o
    JOIN products p ON o.product_id = p.product_id
)
SELECT 
    category,
    brand,
    psku,
    sku,
    COUNT(order_id) as order_frequency,
    SUM(quantity) as total_units,
    SUM(total_value) as total_revenue,
    AVG(quantity) as avg_units_per_order,
    AVG(EXTRACT(EPOCH FROM (order_date - prev_order_date))/86400) as avg_days_between_orders,
    MIN(order_date) as first_order,
    MAX(order_date) as last_order
FROM product_orders
GROUP BY category, brand, psku, sku, product_id
HAVING COUNT(order_id) >= 10
ORDER BY order_frequency DESC
LIMIT 500;

-- ============================================================================
-- Q15: Regional Performance Analysis
-- Purpose: Compare sales across geographic regions
-- ============================================================================
SELECT 
    s.region,
    s.state,
    COUNT(DISTINCT s.store_id) as store_count,
    COUNT(o.order_id) as total_orders,
    SUM(o.total_value) as total_revenue,
    AVG(o.total_value) as avg_order_value,
    SUM(o.quantity) as total_units,
    COUNT(DISTINCT o.product_id) as unique_products,
    COUNT(DISTINCT p.brand) as unique_brands,
    ROUND(SUM(o.total_value) / COUNT(DISTINCT s.store_id), 2) as revenue_per_store
FROM orders o
JOIN stores s ON o.store_id = s.store_id
JOIN products p ON o.product_id = p.product_id
GROUP BY s.region, s.state
ORDER BY total_revenue DESC;

-- ============================================================================
-- Q16: Category Performance Trends
-- Purpose: Track category growth month-over-month
-- ============================================================================
SELECT 
    DATE_TRUNC('month', o.order_date) as month,
    p.category,
    COUNT(o.order_id) as orders,
    SUM(o.total_value) as revenue,
    AVG(o.total_value) as avg_order_value,
    SUM(o.quantity) as units,
    LAG(SUM(o.total_value)) OVER (PARTITION BY p.category ORDER BY DATE_TRUNC('month', o.order_date)) as prev_month_revenue,
    ROUND(100.0 * (SUM(o.total_value) - LAG(SUM(o.total_value)) OVER (PARTITION BY p.category ORDER BY DATE_TRUNC('month', o.order_date))) / 
          NULLIF(LAG(SUM(o.total_value)) OVER (PARTITION BY p.category ORDER BY DATE_TRUNC('month', o.order_date)), 0), 2) as mom_growth_pct
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY month, p.category
ORDER BY month, revenue DESC;

-- ============================================================================
-- Q17: Price Point Analysis
-- Purpose: Understand distribution of orders across price segments
-- ============================================================================
SELECT 
    CASE 
        WHEN total_value < 50 THEN '₹0-50'
        WHEN total_value < 100 THEN '₹50-100'
        WHEN total_value < 200 THEN '₹100-200'
        WHEN total_value < 500 THEN '₹200-500'
        WHEN total_value < 1000 THEN '₹500-1000'
        WHEN total_value < 2000 THEN '₹1000-2000'
        ELSE '₹2000+'
    END as price_segment,
    COUNT(*) as order_count,
    SUM(total_value) as total_revenue,
    AVG(total_value) as avg_order_value,
    AVG(quantity) as avg_quantity,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as order_pct,
    ROUND(100.0 * SUM(total_value) / SUM(SUM(total_value)) OVER (), 2) as revenue_pct
FROM orders
GROUP BY price_segment
ORDER BY MIN(total_value);

-- ============================================================================
-- Q18: Cross-Category Purchase Patterns
-- Purpose: Identify categories frequently purchased together
-- ============================================================================
WITH store_date_categories AS (
    SELECT DISTINCT
        o.store_id,
        o.order_date,
        p.category
    FROM orders o
    JOIN products p ON o.product_id = p.product_id
)
SELECT 
    c1.category as category_1,
    c2.category as category_2,
    COUNT(*) as co_occurrence_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(DISTINCT store_id || '_' || order_date) FROM orders), 2) as co_occurrence_pct
FROM store_date_categories c1
JOIN store_date_categories c2 
    ON c1.store_id = c2.store_id 
    AND c1.order_date = c2.order_date 
    AND c1.category < c2.category
GROUP BY c1.category, c2.category
ORDER BY co_occurrence_count DESC
LIMIT 50;

-- ============================================================================
-- Q19: Top Products per Store Type
-- Purpose: Identify format-specific best sellers
-- ============================================================================
WITH ranked_products AS (
    SELECT 
        s.store_type,
        p.brand,
        p.psku,
        p.sku,
        SUM(o.total_value) as revenue,
        SUM(o.quantity) as units_sold,
        COUNT(o.order_id) as order_count,
        RANK() OVER (PARTITION BY s.store_type ORDER BY SUM(o.total_value) DESC) as revenue_rank
    FROM orders o
    JOIN stores s ON o.store_id = s.store_id
    JOIN products p ON o.product_id = p.product_id
    GROUP BY s.store_type, p.brand, p.psku, p.sku
)
SELECT *
FROM ranked_products
WHERE revenue_rank <= 20
ORDER BY store_type, revenue_rank;

-- ============================================================================
-- Q20: Data Quality Summary
-- Purpose: Comprehensive dataset validation metrics
-- ============================================================================
SELECT 
    'Products' as table_name,
    COUNT(*) as total_rows,
    COUNT(DISTINCT psku_code) as unique_pskus,
    COUNT(DISTINCT sku_code) as unique_skus,
    MIN(unit_price) as min_price,
    MAX(unit_price) as max_price,
    AVG(unit_price) as avg_price,
    NULL::bigint as date_range_days,
    NULL::date as min_date,
    NULL::date as max_date
FROM products

UNION ALL

SELECT 
    'Stores',
    COUNT(*),
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL
FROM stores

UNION ALL

SELECT 
    'Orders',
    COUNT(*),
    NULL,
    NULL,
    MIN(total_value),
    MAX(total_value),
    AVG(total_value),
    MAX(order_date) - MIN(order_date) + 1,
    MIN(order_date),
    MAX(order_date)
FROM orders

UNION ALL

SELECT 
    'Transactions',
    COUNT(*),
    NULL,
    NULL,
    MIN(value),
    MAX(value),
    AVG(value),
    MAX(date) - MIN(date) + 1,
    MIN(date),
    MAX(date)
FROM transactions;