# Task 1 — Get the Olist Data Into a Database

Everything needed to load the Olist Brazilian E-Commerce CSVs into PostgreSQL,
running locally with Docker.

## Folder structure

```
olist_task1/
├── docker-compose.yml       # spins up Postgres (+ pgAdmin) locally
├── init/
│   └── schema.sql            # creates the 9 tables + indexes
├── data/                      # put the 9 Olist CSV files here (from Kaggle)
├── scripts/
│   ├── load_data.py           # loads the CSVs into Postgres
│   └── test_queries.sql       # Step 3 test/verification queries
├── requirements.txt
├── query_output.txt            # verified output from the test queries
├── Task1_Report.docx           # submission report
└── README.md
```

## How to run it

### 1. Get the data
Download the CSVs from Kaggle (link is in `Olist_Dataset_Introduction.pdf`):
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

Unzip them into the `data/` folder so you have:
```
data/olist_customers_dataset.csv
data/olist_geolocation_dataset.csv
data/olist_order_items_dataset.csv
data/olist_order_payments_dataset.csv
data/olist_order_reviews_dataset.csv
data/olist_orders_dataset.csv
data/olist_products_dataset.csv
data/olist_sellers_dataset.csv
data/product_category_name_translation.csv
```

### 2. Start the database (Docker)
```bash
docker compose up -d
```
This starts:
- **postgres** on `localhost:5432` (db=`olist_db`, user=`olist_user`, pass=`olist_pass`) — the schema in `init/schema.sql` is applied automatically on first start.
- **pgadmin** on `localhost:5050` (optional GUI, login `admin@olist.local` / `admin`)

Check it's healthy:
```bash
docker compose ps
docker compose logs postgres --tail 30
```

### 3. Load the CSVs into the database

Windows PowerShell:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts\load_data.py --data-dir .\data
```

Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python scripts/load_data.py --data-dir ./data
```
You should see each table print its row count, e.g.:
```
Loading customers <- ./data/olist_customers_dataset.csv ... 99,441 rows OK
Loading sellers <- ./data/olist_sellers_dataset.csv ... 3,095 rows OK
Loading products <- ./data/olist_products_dataset.csv ... 32,951 rows OK
Loading product_category_translation <- ./data/product_category_name_translation.csv ... 71 rows OK
Loading geolocation <- ./data/olist_geolocation_dataset.csv ... 1,000,163 rows OK
Loading orders <- ./data/olist_orders_dataset.csv ... 99,441 rows OK
Loading order_items <- ./data/olist_order_items_dataset.csv ... 112,650 rows OK
Loading order_payments <- ./data/olist_order_payments_dataset.csv ... 103,886 rows OK
Loading order_reviews <- ./data/olist_order_reviews_dataset.csv ... 99,224 rows OK
```

### 4. Test it (connect + query + join)

No host `psql` installation is required. On Windows PowerShell:

```powershell
Get-Content .\scripts\test_queries.sql |
  docker compose exec -T postgres psql -U olist_user -d olist_db
```

On Linux/macOS:

```bash
docker compose exec -T postgres \
  psql -U olist_user -d olist_db < scripts/test_queries.sql
```

Or connect interactively through the container:

```bash
docker compose exec postgres psql -U olist_user -d olist_db
\dt                      -- list tables
SELECT * FROM orders LIMIT 5;
```

### 5. Shut down (keeps data, since it's in a named volume)
```bash
docker compose down
```
To wipe the data too: `docker compose down -v`

## Schema (ERD)

```
customers ──< orders >──< order_items >── products ── product_category_translation
                │              │
                │              └──< sellers
                ├──< order_payments
                └──< order_reviews

customers.customer_zip_code_prefix ──> geolocation.geolocation_zip_code_prefix
sellers.seller_zip_code_prefix     ──> geolocation.geolocation_zip_code_prefix
```

- **orders** is the central fact table: one row per order.
- **order_items** and **order_payments** are one-to-many with `orders` (an order
  can have several items and several payment installments) — they must be
  aggregated (`GROUP BY order_id`) before joining back to `orders`, otherwise
  the order-level row gets duplicated.
- **order_reviews** is mostly one-to-one with `orders`.
- **geolocation** links to `customers` / `sellers` through the ZIP-code prefix,
  not a dedicated ID.


