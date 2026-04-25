import random
import sqlite3
from database_manager import get_connection, init_db

REGIONS = [("Marmara",), ("Ege",), ("Ic Anadolu",), ("Akdeniz",)]
PACKAGES = [("Eko 5GB", 70.0), ("Mega 20GB", 150.0), ("Pro Sinirsiz", 300.0)]


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

            packages = conn.execute("SELECT package_id, monthly_fee FROM packages").fetchall()
            package_map = {row["package_id"]: row["monthly_fee"] for row in packages}
            region_ids = [row["region_id"] for row in conn.execute("SELECT region_id FROM regions").fetchall()]

            inserted = 0
            for i in range(record_count):
                email = f"ogrenci_{i}@edu.com"
                phone = f"555{random.randint(1000000, 9999999)}"
                try:
                    cursor = conn.execute(
                        "INSERT OR IGNORE INTO customers "
                        "(first_name, last_name, phone_number, email, region_id) VALUES (?,?,?,?,?)",
                        ("Ad", "Soyad", phone, email, random.choice(region_ids)),
                    )
                    c_id = cursor.lastrowid
                    if c_id:
                        p_id = random.choice(list(package_map.keys()))
                        conn.execute(
                            "INSERT INTO subscriptions "
                            "(customer_id, package_id, price_at_purchase) VALUES (?,?,?)",
                            (c_id, p_id, package_map[p_id]),
                        )
                        inserted += 1
                except sqlite3.IntegrityError:
                    continue

        print(f"✅ {inserted} kayıt başarıyla oluşturuldu.")
    except sqlite3.Error as e:
        print(f"Seed hatası: {e}")
        raise


if __name__ == "__main__":
    seed()
