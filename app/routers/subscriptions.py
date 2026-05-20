import sqlite3
from fastapi import APIRouter, HTTPException, Query
from app.database import get_connection
from app.models import SubscriptionCreate, SubscriptionUpdate, SubscriptionDetail

router = APIRouter(prefix="/subscriptions", tags=["Abonelikler"])


@router.get("/", response_model=list[SubscriptionDetail])
def list_subscriptions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = None,
):
    query = """
        SELECT s.subscription_id, c.first_name, c.last_name,
               p.package_name, s.price_at_purchase, s.status,
               s.start_date, s.end_date
        FROM subscriptions s
        JOIN customers c ON s.customer_id = c.customer_id
        JOIN packages  p ON s.package_id  = p.package_id
    """
    params: list = []

    if status:
        query += " WHERE s.status = ?"
        params.append(status)

    query += " ORDER BY s.started_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


@router.post("/", status_code=201)
def create_subscription(data: SubscriptionCreate):
    with get_connection() as conn:
        customer = conn.execute(
            "SELECT customer_id FROM customers WHERE customer_id = ?", (data.customer_id,)
        ).fetchone()
        if not customer:
            raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")

        package = conn.execute(
            "SELECT package_id, monthly_fee FROM packages WHERE package_id = ?", (data.package_id,)
        ).fetchone()
        if not package:
            raise HTTPException(status_code=404, detail="Paket bulunamadı.")

        # Aktif abonelik var mı?
        existing = conn.execute(
            """SELECT subscription_id FROM subscriptions
               WHERE customer_id = ? AND package_id = ? AND status = 'active'""",
            (data.customer_id, data.package_id),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Müşteri bu pakete zaten abone.")

        cursor = conn.execute(
            """INSERT INTO subscriptions
               (customer_id, package_id, price_at_purchase, start_date, end_date)
               VALUES (?, ?, ?, ?, ?)""",
            (data.customer_id, data.package_id, dict(package)["monthly_fee"],
             str(data.start_date) if data.start_date else None,
             str(data.end_date) if data.end_date else None),
        )
        return {"subscription_id": cursor.lastrowid, "status": "active"}


@router.patch("/{subscription_id}", status_code=200)
def update_subscription_status(subscription_id: int, data: SubscriptionUpdate):
    with get_connection() as conn:
        result = conn.execute(
            "UPDATE subscriptions SET status = ? WHERE subscription_id = ?",
            (data.status, subscription_id),
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Abonelik bulunamadı.")
        return {"subscription_id": subscription_id, "status": data.status}


@router.get("/stats/by-package")
def stats_by_package():
    """Paket bazında abonelik sayısı ve toplam gelir."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT p.package_name,
                      COUNT(s.subscription_id) as total_subscribers,
                      SUM(s.price_at_purchase) as total_revenue
               FROM packages p
               LEFT JOIN subscriptions s ON p.package_id = s.package_id AND s.status = 'active'
               GROUP BY p.package_id
               ORDER BY total_revenue DESC"""
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/stats/by-region")
def stats_by_region():
    """Bölge bazında aktif abonelik sayısı."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT r.region_name,
                      COUNT(s.subscription_id) as active_subscriptions
               FROM regions r
               LEFT JOIN customers c ON r.region_id = c.region_id
               LEFT JOIN subscriptions s ON c.customer_id = s.customer_id AND s.status = 'active'
               GROUP BY r.region_id
               ORDER BY active_subscriptions DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
