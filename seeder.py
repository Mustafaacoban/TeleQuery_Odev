import random
import sqlite3
import sys
from faker import Faker
from app.database import get_connection, init_db

fake = Faker("tr_TR")

REGIONS = [("Marmara",), ("Ege",), ("İç Anadolu",), ("Akdeniz",), ("Karadeniz",), ("Doğu Anadolu",)]
PACKAGES = [
    ("Eko 5GB", 70.0),
    ("Mega 20GB", 150.0),
    ("Pro Sınırsız", 300.0),
    ("Aile Paketi", 450.0),
]


def seed(record_count: int = 1000):
    init_db()
    try:
        with get_connection() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO regions (region_name) VALUES (?)", REGIONS
            )
            conn.executemany(
                "INSERT OR IGNORE INTO packages (package_name, monthly_fee) VALUES (?,?)",
                PACKAGES,
            )

            packages = conn.execute(
                "SELECT package_id, monthly_fee FROM packages"
            ).fetchall()
            package_map = {row["package_id"]: row["monthly_fee"] for row in packages}

            region_ids = [
                row["region_id"]
                for row in conn.execute("SELECT region_id FROM regions").fetchall()
            ]

            inserted = 0
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
                    conn.execute(
                        """INSERT INTO subscriptions
                           (customer_id, package_id, price_at_purchase)
                           VALUES (?, ?, ?)""",
                        (c_id, p_id, package_map[p_id]),
                    )
                    inserted += 1
                except sqlite3.IntegrityError:
                    continue

        print(f"✅ {inserted} kayıt başarıyla oluşturuldu.")
    except sqlite3.Error as e:
        print(f"❌ Seed hatası: {e}")
        raise


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    seed(count)
