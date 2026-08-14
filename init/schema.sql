-- ============================================================
-- Olist Brazilian E-Commerce – Database Schema
-- 
-- ============================================================

DROP TABLE IF EXISTS order_reviews CASCADE;
DROP TABLE IF EXISTS order_payments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS sellers CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS geolocation CASCADE;
DROP TABLE IF EXISTS product_category_translation CASCADE;

-- Customers: one row per customer record linked to an order
CREATE TABLE customers (
    customer_id             VARCHAR(32) PRIMARY KEY,
    customer_unique_id      VARCHAR(32) NOT NULL,
    customer_zip_code_prefix VARCHAR(10),
    customer_city           VARCHAR(100),
    customer_state          VARCHAR(2)
);

-- Sellers
CREATE TABLE sellers (
    seller_id             VARCHAR(32) PRIMARY KEY,
    seller_zip_code_prefix VARCHAR(10),
    seller_city            VARCHAR(100),
    seller_state            VARCHAR(2)
);

-- Products
CREATE TABLE products (
    product_id                 VARCHAR(32) PRIMARY KEY,
    product_category_name      VARCHAR(100),
    product_name_lenght        NUMERIC,
    product_description_lenght NUMERIC,
    product_photos_qty         NUMERIC,
    product_weight_g           NUMERIC,
    product_length_cm          NUMERIC,
    product_height_cm          NUMERIC,
    product_width_cm           NUMERIC
);

-- Product category name translation (PT -> EN)
CREATE TABLE product_category_translation (
    product_category_name          VARCHAR(100) PRIMARY KEY,
    product_category_name_english  VARCHAR(100)
);

-- Geolocation (many rows per zip prefix)
CREATE TABLE geolocation (
    geolocation_zip_code_prefix VARCHAR(10),
    geolocation_lat              NUMERIC,
    geolocation_lng              NUMERIC,
    geolocation_city             VARCHAR(100),
    geolocation_state            VARCHAR(2)
);

-- Orders: one row per order
CREATE TABLE orders (
    order_id                       VARCHAR(32) PRIMARY KEY,
    customer_id                    VARCHAR(32) REFERENCES customers(customer_id),
    order_status                   VARCHAR(20),
    order_purchase_timestamp       TIMESTAMP,
    order_approved_at              TIMESTAMP,
    order_delivered_carrier_date   TIMESTAMP,
    order_delivered_customer_date  TIMESTAMP,
    order_estimated_delivery_date  TIMESTAMP
);

-- Order items: one row per item inside an order
CREATE TABLE order_items (
    order_id             VARCHAR(32) REFERENCES orders(order_id),
    order_item_id         INTEGER,
    product_id            VARCHAR(32) REFERENCES products(product_id),
    seller_id             VARCHAR(32) REFERENCES sellers(seller_id),
    shipping_limit_date    TIMESTAMP,
    price                  NUMERIC(10,2),
    freight_value          NUMERIC(10,2),
    PRIMARY KEY (order_id, order_item_id)
);

-- Order payments: one row per payment record for an order
CREATE TABLE order_payments (
    order_id             VARCHAR(32) REFERENCES orders(order_id),
    payment_sequential    INTEGER,
    payment_type          VARCHAR(20),
    payment_installments  INTEGER,
    payment_value         NUMERIC(10,2),
    PRIMARY KEY (order_id, payment_sequential)
);

-- Order reviews: one row per customer review
CREATE TABLE order_reviews (
    review_id                VARCHAR(32),
    order_id                  VARCHAR(32) REFERENCES orders(order_id),
    review_score              INTEGER,
    review_comment_title      TEXT,
    review_comment_message    TEXT,
    review_creation_date      TIMESTAMP,
    review_answer_timestamp   TIMESTAMP,
    PRIMARY KEY (review_id, order_id)
);

-- Helpful indexes for joins used later in the ML pipeline
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_items_order_id ON order_items(order_id);
CREATE INDEX idx_items_product_id ON order_items(product_id);
CREATE INDEX idx_items_seller_id ON order_items(seller_id);
CREATE INDEX idx_payments_order_id ON order_payments(order_id);
CREATE INDEX idx_reviews_order_id ON order_reviews(order_id);
CREATE INDEX idx_customers_zip ON customers(customer_zip_code_prefix);
CREATE INDEX idx_sellers_zip ON sellers(seller_zip_code_prefix);
CREATE INDEX idx_geo_zip ON geolocation(geolocation_zip_code_prefix);
