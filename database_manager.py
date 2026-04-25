import sqlite3
from contextlib import contextmanager

DB_NAME = "tele_query.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS regions (
    region_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    region_name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS packages (
    package_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    package_name TEXT NOT NULL,
    monthly_fee  DECIMAL(8,2) NOT NULL
);
CREATE TABLE IF NOT EXISTS customers (
    customer_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name   TEXT NOT NULL,
    last_name    TEXT NOT NULL,
    phone_number TEXT UNIQUE NOT NULL,
    email        TEXT UNIQUE NOT NULL,
    region_id    INTEGER,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (region_id) REFERENCES regions(region_id)
);
CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id       INTEGER NOT NULL,
    package_id        INTEGER NOT NULL,
    price_at_purchase DECIMAL(8,2) NOT NULL,
    status            TEXT DEFAULT 'active',
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (package_id)  REFERENCES packages(package_id)
);
"""


@contextmanager
def get_connection(db_name: str = DB_NAME):
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_name: str = DB_NAME):
    try:
        with get_connection(db_name) as conn:
            conn.executescript(SCHEMA)
        print("Veritabanı başlatıldı.")
    except sqlite3.Error as e:
        print(f"Veritabanı başlatma hatası: {e}")
        raise
