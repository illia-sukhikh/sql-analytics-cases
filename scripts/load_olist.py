"""Load the Olist e-commerce CSV files into PostgreSQL.

Usage:
    1. Download the dataset from Kaggle and unzip the CSV files into data/raw/
    2. Copy .env.example to .env and set DATABASE_URL
    3. pip install -r requirements.txt
    4. python scripts/load_olist.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"

# CSV file -> (table name, timestamp columns to parse)
TABLES: dict[str, tuple[str, list[str]]] = {
    "olist_customers_dataset.csv": ("customers", []),
    "olist_geolocation_dataset.csv": ("geolocation", []),
    "olist_order_items_dataset.csv": ("order_items", ["shipping_limit_date"]),
    "olist_order_payments_dataset.csv": ("order_payments", []),
    "olist_order_reviews_dataset.csv": (
        "order_reviews",
        ["review_creation_date", "review_answer_timestamp"],
    ),
    "olist_orders_dataset.csv": (
        "orders",
        [
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    ),
    "olist_products_dataset.csv": ("products", []),
    "olist_sellers_dataset.csv": ("sellers", []),
    "product_category_name_translation.csv": ("category_translation", []),
}

INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_orders_customer ON orders (customer_id)",
    "CREATE INDEX IF NOT EXISTS ix_order_items_order ON order_items (order_id)",
    "CREATE INDEX IF NOT EXISTS ix_order_items_product ON order_items (product_id)",
    "CREATE INDEX IF NOT EXISTS ix_order_items_seller ON order_items (seller_id)",
    "CREATE INDEX IF NOT EXISTS ix_order_payments_order ON order_payments (order_id)",
    "CREATE INDEX IF NOT EXISTS ix_order_reviews_order ON order_reviews (order_id)",
]

# PostgreSQL accepts at most 65,535 parameters per statement:
# keep rows_per_batch * number_of_columns below that limit.
MAX_PARAMS_PER_INSERT = 60_000


def load_table(engine, csv_path: Path, table: str, date_cols: list[str]) -> int:
    df = pd.read_csv(csv_path, parse_dates=date_cols)
    rows_per_batch = max(1, MAX_PARAMS_PER_INSERT // len(df.columns))
    df.to_sql(
        table,
        engine,
        if_exists="replace",
        index=False,
        chunksize=rows_per_batch,
        method="multi",
    )
    return len(df)


def main() -> int:
    load_dotenv(PROJECT_DIR / ".env")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set. Copy .env.example to .env and fill it in.")
        return 1

    missing = [name for name in TABLES if not (RAW_DIR / name).exists()]
    if missing:
        print(f"Missing files in {RAW_DIR}:")
        for name in missing:
            print(f"  - {name}")
        return 1

    engine = create_engine(database_url)
    for file_name, (table, date_cols) in TABLES.items():
        rows = load_table(engine, RAW_DIR / file_name, table, date_cols)
        print(f"{table:<22}{rows:>10,} rows")

    with engine.begin() as conn:
        for statement in INDEXES:
            conn.execute(text(statement))

    print("Done. Next step: run sql/00_check_load.sql")
    return 0


if __name__ == "__main__":
    sys.exit(main())
