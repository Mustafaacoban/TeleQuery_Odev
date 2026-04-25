import sqlite3
import random
from datetime import datetime

class TeleQuerySystem:
    def __init__(self, db_name="tele_query.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.setup_database()

    def setup_database(self):
        schema = """
        CREATE TABLE IF NOT EXISTS regions (
            region_id INTEGER PRIMARY KEY AUTOINCREMENT,
            region_name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS packages (
            package_id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_name TEXT NOT NULL,
            monthly_fee DECIMAL(8,2) NOT NULL
        );
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            phone_number TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            region_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (region_id) REFERENCES regions(region_id)
        );
        CREATE TABLE IF NOT EXISTS subscriptions (
            subscription_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            package_id INTEGER NOT NULL,
            price_at_purchase DECIMAL(8,2) NOT NULL,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY (package_id) REFERENCES packages(package_id)
        );
        """
        self.cursor.executescript(schema)
        self.conn.commit()

    def seed_data(self):
        # Temel verileri ekle
        regions = [("Marmara",), ("Ege",), ("Ic Anadolu",), ("Akdeniz",)]
        self.cursor.executemany("INSERT OR IGNORE INTO regions (region_name) VALUES (?)", regions)
        
        packages = [("Eko 5GB", 70.0), ("Mega 20GB", 150.0), ("Pro Sinirsiz", 300.0)]
        self.cursor.executemany("INSERT OR IGNORE INTO packages (package_name, monthly_fee) VALUES (?,?)", packages)
        
        # 1000 Örnek Kayıt Üret
        for i in range(1000):
            email = f"ogrenci_{i}@edu.com"
            phone = f"555{random.randint(1000000, 9999999)}"
            self.cursor.execute("INSERT OR IGNORE INTO customers (first_name, last_name, phone_number, email, region_id) VALUES (?,?,?,?,?)",
                               ("Ad", "Soyad", phone, email, random.randint(1, 4)))
            
            c_id = self.cursor.lastrowid
            if c_id:
                p_id = random.randint(1, 3)
                self.cursor.execute("SELECT monthly_fee FROM packages WHERE package_id = ?", (p_id,))
                price = self.cursor.fetchone()[0]
                self.cursor.execute("INSERT INTO subscriptions (customer_id, package_id, price_at_purchase) VALUES (?,?,?)",
                                   (c_id, p_id, price))
        
        self.conn.commit()
        print("✅ 1000 Kayıt Başarıyla Oluşturuldu!")

if __name__ == "__main__":
    app = TeleQuerySystem()
    app.seed_data()
