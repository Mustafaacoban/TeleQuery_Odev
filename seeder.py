import random
import sqlite3
import sys
from datetime import datetime, timedelta
from faker import Faker
from app.database import get_connection, init_db

fake = Faker("tr_TR")

REGIONS = [
    ("Marmara",    "MRM"),
    ("Ege",        "EGE"),
    ("İç Anadolu", "ICA"),
    ("Akdeniz",    "AKD"),
    ("Karadeniz",  "KRD"),
    ("Doğu Anadolu", "DGA"),
]

PACKAGES = [
    # (name, monthly_fee, speed_mbps, quota_gb)
    ("Eko 5GB",      70.0,  25,  5),
    ("Mega 20GB",   150.0,  50, 20),
    ("Pro Sınırsız", 300.0, 100, None),
    ("Aile Paketi",  450.0, 150, None),
]

EMPLOYEES = [
    ("Ahmet",   "Çelik",  "Destek Elemanı"),
    ("Fatma",   "Kaya",   "Destek Elemanı"),
    ("Mehmet",  "Demir",  "Yönetici"),
    ("Ayşe",    "Yıldız", "Teknik Uzman"),
    ("Ali",     "Şahin",  "Destek Elemanı"),
    ("Zeynep",  "Arslan", "Teknik Uzman"),
    ("Mustafa", "Koç",    "Yönetici"),
]

TICKET_SUBJECTS = [
    "İnternet bağlantısı yok",
    "Yavaş internet hızı",
    "Fatura tutarı hatalı",
    "Paket değişikliği talebi",
    "Modem arızası",
    "Şifre sıfırlama",
    "Fatura iptali talebi",
]


def seed(record_count: int = 1000):
    init_db()
    try:
        with get_connection() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO regions (region_name, code) VALUES (?,?)", REGIONS
            )
            conn.executemany(
                "INSERT OR IGNORE INTO packages (package_name, monthly_fee, speed_mbps, quota_gb) VALUES (?,?,?,?)",
                PACKAGES,
            )
            conn.executemany(
                "INSERT OR IGNORE INTO employees (first_name, last_name, title) VALUES (?,?,?)",
                EMPLOYEES,
            )

            packages = conn.execute(
                "SELECT package_id, monthly_fee FROM packages"
            ).fetchall()
            package_map = {row["package_id"]: row["monthly_fee"] for row in packages}

            region_ids = [
                row["region_id"]
                for row in conn.execute("SELECT region_id FROM regions").fetchall()
            ]
            employee_ids = [
                row["employee_id"]
                for row in conn.execute("SELECT employee_id FROM employees").fetchall()
            ]

            inserted = 0
            subscription_data = []
            today = datetime.now()

            for _ in range(record_count):
                try:
                    cursor = conn.execute(
                        """INSERT INTO customers
                           (first_name, last_name, phone_number, email, region_id)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            fake.first_name(),
                            fake.last_name(),
                            fake.unique.phone_number(),
                            fake.unique.email(),
                            random.choice(region_ids),
                        ),
                    )
                    c_id = cursor.lastrowid
                    p_id = random.choice(list(package_map.keys()))
                    start = today - timedelta(days=random.randint(30, 365))
                    sub_cursor = conn.execute(
                        """INSERT INTO subscriptions
                           (customer_id, package_id, price_at_purchase, start_date)
                           VALUES (?, ?, ?, ?)""",
                        (c_id, p_id, package_map[p_id], start.strftime("%Y-%m-%d")),
                    )
                    subscription_data.append((sub_cursor.lastrowid, package_map[p_id], c_id))
                    inserted += 1
                except sqlite3.IntegrityError:
                    continue

            # Faturalar: son 3 ay, her aboneliğe 3 fatura
            invoice_data = []
            for sub_id, price, _ in subscription_data:
                for month_offset in range(3):
                    due = (today - timedelta(days=30 * month_offset)).strftime("%Y-%m-%d")
                    status = "Unpaid" if month_offset == 0 else "Paid"
                    inv_cursor = conn.execute(
                        "INSERT INTO invoices (subscription_id, amount, due_date, status) VALUES (?,?,?,?)",
                        (sub_id, price, due, status),
                    )
                    invoice_data.append((inv_cursor.lastrowid, price, status))

            # Ödemeler (Paid faturaları için)
            for inv_id, amount, status in invoice_data:
                if status == "Paid":
                    conn.execute(
                        "INSERT INTO payments (invoice_id, amount, payment_method) VALUES (?,?,?)",
                        (inv_id, amount, random.choice(["Credit Card", "Bank Transfer", "EFT"])),
                    )

            # Destek talepleri (~%30 müşteri)
            customer_ids = [row[2] for row in subscription_data]
            sample_size = max(1, len(customer_ids) // 3)
            for c_id in random.sample(customer_ids, sample_size):
                conn.execute(
                    """INSERT INTO support_tickets
                       (customer_id, employee_id, subject, status)
                       VALUES (?,?,?,?)""",
                    (
                        c_id,
                        random.choice(employee_ids),
                        random.choice(TICKET_SUBJECTS),
                        random.choice(["Open", "In Progress", "Resolved"]),
                    ),
                )

        print(f"✅ {inserted} müşteri ve abonelik kaydı oluşturuldu.")
        print(f"✅ {inserted * 3} fatura, ~{inserted * 2} ödeme kaydedildi.")
        print(f"✅ ~{inserted // 3} destek talebi oluşturuldu.")
    except sqlite3.Error as e:
        print(f"❌ Seed hatası: {e}")
        raise


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    seed(count)
