-- ============================================================
-- Step 3: Test queries (reads + joins)
-- ============================================================

-- 1) Row counts per table
SELECT 'customers' AS table_name, COUNT(*) FROM customers
UNION ALL SELECT 'sellers', COUNT(*) FROM sellers
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'product_category_translation', COUNT(*) FROM product_category_translation
UNION ALL SELECT 'geolocation', COUNT(*) FROM geolocation
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'order_payments', COUNT(*) FROM order_payments
UNION ALL SELECT 'order_reviews', COUNT(*) FROM order_reviews;

-- 2) Simple read: first 5 orders
SELECT order_id, order_status, order_purchase_timestamp, order_estimated_delivery_date
FROM orders
LIMIT 5;

-- 3) Two-table join: orders + customers (state of each customer)
SELECT o.order_id, o.order_status, c.customer_city, c.customer_state
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
LIMIT 5;

-- 4) Multi-table join: order -> items -> products -> sellers
SELECT o.order_id, p.product_category_name, s.seller_state, oi.price, oi.freight_value
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
JOIN sellers s ON oi.seller_id = s.seller_id
LIMIT 5;

-- 5) Aggregation: total order value (items + freight) per order, joined with payments total
--    (this also demonstrates the "aggregate before join" lesson from the PDF)
WITH item_totals AS (
    SELECT order_id,
           SUM(price) AS items_total,
           SUM(freight_value) AS freight_total
    FROM order_items
    GROUP BY order_id
),
payment_totals AS (
    SELECT order_id, SUM(payment_value) AS payment_total
    FROM order_payments
    GROUP BY order_id
)
SELECT o.order_id, i.items_total, i.freight_total, p.payment_total
FROM orders o
JOIN item_totals i ON o.order_id = i.order_id
JOIN payment_totals p ON o.order_id = p.order_id
LIMIT 5;

-- 6) The target variable for the ML problem: late vs on-time delivery
SELECT
    order_id,
    order_delivered_customer_date,
    order_estimated_delivery_date,
    CASE
        WHEN order_delivered_customer_date IS NULL THEN NULL
        WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 1
        ELSE 0
    END AS is_late
FROM orders
WHERE order_status = 'delivered'
LIMIT 5;

-- 7) Class balance of the target (only delivered orders have a real delivery date)
SELECT
    CASE
        WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 'late'
        ELSE 'on_time'
    END AS delivery_class,
    COUNT(*) AS num_orders,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM orders
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL
GROUP BY 1;

-- 8) Average review score per order status (sanity check join across 3 tables)
SELECT o.order_status, ROUND(AVG(r.review_score)::numeric, 2) AS avg_review_score, COUNT(*) AS n
FROM orders o
JOIN order_reviews r ON o.order_id = r.order_id
GROUP BY o.order_status
ORDER BY n DESC;
