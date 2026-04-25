import sqlite3
from fastapi import FastAPI, HTTPException
from database_manager import get_connection, init_db

app = FastAPI(title="TeleQuery API")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/regions")
def list_regions():
    try:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM regions").fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/packages")
def list_packages():
    try:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM packages").fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/customers")
def list_customers(limit: int = 20, offset: int = 0):
    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM customers LIMIT ? OFFSET ?", (limit, offset)
            ).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/customers/{customer_id}")
def get_customer(customer_id: int):
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")
            return dict(row)
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/customers/{customer_id}/subscriptions")
def get_customer_subscriptions(customer_id: int):
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT s.subscription_id, p.package_name, s.price_at_purchase, s.status
                FROM subscriptions s
                JOIN packages p ON s.package_id = p.package_id
                WHERE s.customer_id = ?
                """,
                (customer_id,),
            ).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/subscriptions")
def list_subscriptions(limit: int = 20, offset: int = 0):
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT s.subscription_id, c.first_name, c.last_name,
                       p.package_name, s.price_at_purchase, s.status
                FROM subscriptions s
                JOIN customers c ON s.customer_id = c.customer_id
                JOIN packages  p ON s.package_id  = p.package_id
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
