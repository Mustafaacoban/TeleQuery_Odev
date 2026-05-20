import os
import sqlite3
from contextlib import contextmanager

DB_NAME = os.getenv("DATABASE_URL", "tele_query.db")

# ─── TABLO & VIEW ŞEMASI ────────────────────────────────────────────────────
TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS regions (
    region_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    region_name TEXT NOT NULL UNIQUE,
    code        TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS packages (
    package_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    package_name TEXT NOT NULL,
    monthly_fee  REAL NOT NULL,
    speed_mbps   INTEGER NOT NULL DEFAULT 0,
    quota_gb     INTEGER
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
    price_at_purchase REAL NOT NULL,
    status            TEXT DEFAULT 'active' CHECK(status IN ('active', 'cancelled', 'suspended')),
    started_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    start_date        DATE,
    end_date          DATE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (package_id)  REFERENCES packages(package_id)
);
CREATE TABLE IF NOT EXISTS employees (
    employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name  TEXT NOT NULL,
    last_name   TEXT NOT NULL,
    title       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER NOT NULL,
    amount          REAL NOT NULL,
    due_date        DATE NOT NULL,
    status          TEXT DEFAULT 'Unpaid' CHECK(status IN ('Unpaid', 'Paid', 'Overdue')),
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(subscription_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS payments (
    payment_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id     INTEGER NOT NULL,
    payment_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    amount         REAL NOT NULL,
    payment_method TEXT NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS support_tickets (
    ticket_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    employee_id INTEGER,
    subject     TEXT NOT NULL,
    description TEXT,
    status      TEXT DEFAULT 'Open' CHECK(status IN ('Open', 'In Progress', 'Resolved', 'Closed')),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS customer_logs (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    action_type TEXT,
    old_data    TEXT,
    new_data    TEXT,
    changed_by  TEXT DEFAULT 'SYSTEM',
    changed_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS revenue_stats_log (
    log_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    log_message            TEXT,
    total_revenue_snapshot REAL,
    recorded_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE VIEW IF NOT EXISTS v_customer_dashboard AS
SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_full_name,
    r.region_name,
    p.package_name,
    p.speed_mbps,
    p.quota_gb,
    s.status AS subscription_status,
    s.start_date,
    s.end_date,
    COALESCE(SUM(CASE WHEN i.status = 'Unpaid' THEN i.amount ELSE 0 END), 0) AS total_unpaid_debt
FROM customers c
LEFT JOIN regions r ON c.region_id = r.region_id
LEFT JOIN subscriptions s ON c.customer_id = s.customer_id
LEFT JOIN packages p ON s.package_id = p.package_id
LEFT JOIN invoices i ON s.subscription_id = i.subscription_id
GROUP BY c.customer_id, c.first_name, c.last_name, r.region_name,
         p.package_name, p.speed_mbps, p.quota_gb, s.status, s.start_date, s.end_date;
"""

# ─── TRIGGER ŞEMASI ─────────────────────────────────────────────────────────
# old_data / new_data JSON formatında loglanır (PostgreSQL ROW_TO_JSON karşılığı)
TRIGGER_SCHEMA = [
    """
    CREATE TRIGGER IF NOT EXISTS trg_customer_audit_update
    AFTER UPDATE ON customers
    FOR EACH ROW
    BEGIN
        INSERT INTO customer_logs(customer_id, action_type, old_data, new_data, changed_by)
        VALUES (
            OLD.customer_id, 'UPDATE',
            '{"customer_id":' || OLD.customer_id ||
            ',"first_name":"' || OLD.first_name ||
            '","last_name":"'  || OLD.last_name  ||
            '","email":"'      || OLD.email       ||
            '","phone":"'      || OLD.phone_number ||
            '","region_id":'   || IFNULL(CAST(OLD.region_id AS TEXT), 'null') || '}',
            '{"customer_id":' || NEW.customer_id ||
            ',"first_name":"' || NEW.first_name ||
            '","last_name":"'  || NEW.last_name  ||
            '","email":"'      || NEW.email       ||
            '","phone":"'      || NEW.phone_number ||
            '","region_id":'   || IFNULL(CAST(NEW.region_id AS TEXT), 'null') || '}',
            'SYSTEM'
        );
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_customer_audit_delete
    AFTER DELETE ON customers
    FOR EACH ROW
    BEGIN
        INSERT INTO customer_logs(customer_id, action_type, old_data, new_data, changed_by)
        VALUES (
            OLD.customer_id, 'DELETE',
            '{"customer_id":' || OLD.customer_id ||
            ',"first_name":"' || OLD.first_name ||
            '","last_name":"'  || OLD.last_name  ||
            '","email":"'      || OLD.email       ||
            '","phone":"'      || OLD.phone_number ||
            '","region_id":'   || IFNULL(CAST(OLD.region_id AS TEXT), 'null') || '}',
            NULL, 'SYSTEM'
        );
    END
    """,
]


# ─── SQL FONKSİYONU KAYDI ────────────────────────────────────────────────────
# PostgreSQL'deki CREATE FUNCTION karşılığı:
# fn_get_customer_debt(customer_id) SQL içinden doğrudan çağrılabilir.
def _register_functions(conn: sqlite3.Connection, db_name: str) -> None:
    def _fn_get_customer_debt(customer_id: int) -> float:
        _c = sqlite3.connect(db_name)
        _c.row_factory = sqlite3.Row
        row = _c.execute(
            """SELECT COALESCE(SUM(i.amount), 0) AS d
               FROM invoices i
               JOIN subscriptions s ON i.subscription_id = s.subscription_id
               WHERE s.customer_id = ? AND i.status = 'Unpaid'""",
            (customer_id,),
        ).fetchone()
        _c.close()
        return float(row["d"]) if row else 0.0

    conn.create_function("fn_get_customer_debt", 1, _fn_get_customer_debt)


# ─── BAĞLANTI YÖNETİMİ ──────────────────────────────────────────────────────
@contextmanager
def get_connection(db_name: str | None = None):
    # None olduğunda modül değişkenini call-time'da okur;
    # bu sayede monkeypatch ile değiştirilen DB_NAME testi izole eder.
    if db_name is None:
        db_name = DB_NAME
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _register_functions(conn, db_name)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_name: str = DB_NAME):
    with get_connection(db_name) as conn:
        conn.executescript(TABLE_SCHEMA)
        for trigger_sql in TRIGGER_SCHEMA:
            conn.execute(trigger_sql)


# ─── PYTHON FONKSİYON VERSİYONU (doğrudan conn ile kullanım için) ───────────
def fn_get_customer_debt(conn, customer_id: int) -> float:
    row = conn.execute(
        """SELECT COALESCE(SUM(i.amount), 0) AS total_debt
           FROM invoices i
           JOIN subscriptions s ON i.subscription_id = s.subscription_id
           WHERE s.customer_id = ? AND i.status = 'Unpaid'""",
        (customer_id,),
    ).fetchone()
    return float(row["total_debt"]) if row else 0.0


# ─── STORED PROCEDURE + TRANSACTION ─────────────────────────────────────────
# PostgreSQL CREATE PROCEDURE karşılığı.
# Hata → get_connection() context manager otomatik ROLLBACK yapar.
def sp_process_payment(conn, invoice_id: int, amount: float, method: str) -> dict:
    invoice = conn.execute(
        "SELECT * FROM invoices WHERE invoice_id = ?", (invoice_id,)
    ).fetchone()
    if not invoice:
        raise ValueError("Fatura bulunamadı, Transaction iptal ediliyor!")

    conn.execute(
        "INSERT INTO payments (invoice_id, amount, payment_method) VALUES (?, ?, ?)",
        (invoice_id, amount, method),
    )
    conn.execute(
        "UPDATE invoices SET status = 'Paid' WHERE invoice_id = ?", (invoice_id,)
    )

    total = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS t FROM payments"
    ).fetchone()["t"]
    conn.execute(
        "INSERT INTO revenue_stats_log (log_message, total_revenue_snapshot) VALUES (?, ?)",
        (f"Fatura #{invoice_id} ödendi. Yöntem: {method}", total),
    )

    return {"invoice_id": invoice_id, "status": "Paid", "payment_method": method}
