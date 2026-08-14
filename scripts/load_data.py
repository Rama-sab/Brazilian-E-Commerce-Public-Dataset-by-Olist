
import argparse
import io
import os
import sys

import pandas as pd
import psycopg2

DB_CONFIG = dict(
    host=os.environ.get("PGHOST", "localhost"),
    port=os.environ.get("PGPORT", "5432"),
    dbname=os.environ.get("PGDATABASE", "olist_db"),
    user=os.environ.get("PGUSER", "olist_user"),
    password=os.environ.get("PGPASSWORD", "olist_pass"),
)


TABLE_FILE_MAP = [
    ("customers", "olist_customers_dataset.csv"),
    ("sellers", "olist_sellers_dataset.csv"),
    ("products", "olist_products_dataset.csv"),
    ("product_category_translation", "product_category_name_translation.csv"),
    ("geolocation", "olist_geolocation_dataset.csv"),
    ("orders", "olist_orders_dataset.csv"),
    ("order_items", "olist_order_items_dataset.csv"),
    ("order_payments", "olist_order_payments_dataset.csv"),
    ("order_reviews", "olist_order_reviews_dataset.csv"),
]

TABLE_COLUMNS = {
    "customers": ["customer_id", "customer_unique_id", "customer_zip_code_prefix",
                  "customer_city", "customer_state"],
    "sellers": ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
    "products": ["product_id", "product_category_name", "product_name_lenght",
                 "product_description_lenght", "product_photos_qty", "product_weight_g",
                 "product_length_cm", "product_height_cm", "product_width_cm"],
    "product_category_translation": ["product_category_name", "product_category_name_english"],
    "geolocation": ["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng",
                     "geolocation_city", "geolocation_state"],
    "orders": ["order_id", "customer_id", "order_status", "order_purchase_timestamp",
               "order_approved_at", "order_delivered_carrier_date",
               "order_delivered_customer_date", "order_estimated_delivery_date"],
    "order_items": ["order_id", "order_item_id", "product_id", "seller_id",
                     "shipping_limit_date", "price", "freight_value"],
    "order_payments": ["order_id", "payment_sequential", "payment_type",
                        "payment_installments", "payment_value"],
    "order_reviews": ["review_id", "order_id", "review_score", "review_comment_title",
                       "review_comment_message", "review_creation_date",
                       "review_answer_timestamp"],
}


def load_table(cur, conn, table, csv_path):
    print(f"Loading {table} <- {csv_path} ...", end=" ", flush=True)
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    cols = TABLE_COLUMNS[table]
    df = df[cols]

    if table == "order_reviews":
        df = df.drop_duplicates(subset=["review_id", "order_id"])
    if table == "order_payments":
        df = df.drop_duplicates(subset=["order_id", "payment_sequential"])
    if table == "order_items":
        df = df.drop_duplicates(subset=["order_id", "order_item_id"])

    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, na_rep="\\N")
    buf.seek(0)

    col_list = ", ".join(cols)
    cur.copy_expert(
        f"COPY {table} ({col_list}) FROM STDIN WITH (FORMAT csv, NULL '\\N')",
        buf,
    )
    conn.commit()
    print(f"{len(df):,} rows OK")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="./data", help="Folder with the Olist CSV files")
    args = parser.parse_args()

    missing_files = [
        os.path.join(args.data_dir, filename)
        for _, filename in TABLE_FILE_MAP
        if not os.path.exists(os.path.join(args.data_dir, filename))
    ]
    if missing_files:
        print("ERROR: All 9 Olist CSV files are required. Missing:")
        for path in missing_files:
            print(f"  - {path}")
        return 2

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    try:
        for table, filename in TABLE_FILE_MAP:
            csv_path = os.path.join(args.data_dir, filename)
            cur.execute(f"TRUNCATE TABLE {table} CASCADE;")
            conn.commit()
            load_table(cur, conn, table, csv_path)
    finally:
        cur.close()
        conn.close()

    print("\nAll tables loaded successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
