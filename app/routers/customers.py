import sqlite3
from fastapi import APIRouter, HTTPException, Query
from app.database import get_connection
from app.models import CustomerCreate, CustomerUpdate, CustomerResponse, SubscriptionResponse

router = APIRouter(prefix="/customers", tags=["Müşteriler"])


@router.get("/dashboard")
def customer_dashboard(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """VIEW: Müşteri başına bölge, paket, abonelik durumu ve ödenmemiş borç özeti."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM v_customer_dashboard LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/", response_model=list[CustomerResponse])
def list_customers(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    region_id: int | None = None,
):
    query = "SELECT * FROM customers"
    params: list = []

    if region_id is not None:
        query += " WHERE region_id = ?"
        params.append(region_id)

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")
        return dict(row)


@router.post("/", response_model=CustomerResponse, status_code=201)
def create_customer(data: CustomerCreate):
    try:
        with get_connection() as conn:
            # Bölge var mı kontrol et
            if data.region_id:
                region = conn.execute(
                    "SELECT region_id FROM regions WHERE region_id = ?", (data.region_id,)
                ).fetchone()
                if not region:
                    raise HTTPException(status_code=404, detail="Bölge bulunamadı.")

            cursor = conn.execute(
                """INSERT INTO customers
                   (first_name, last_name, phone_number, email, region_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (data.first_name, data.last_name, data.phone_number,
                 data.email, data.region_id),
            )
            c_id = cursor.lastrowid
            row = conn.execute(
                "SELECT * FROM customers WHERE customer_id = ?", (c_id,)
            ).fetchone()
            return dict(row)
    except sqlite3.IntegrityError as e:
        if "email" in str(e):
            raise HTTPException(status_code=409, detail="Bu email zaten kayıtlı.")
        if "phone" in str(e):
            raise HTTPException(status_code=409, detail="Bu telefon numarası zaten kayıtlı.")
        raise HTTPException(status_code=409, detail="Veri çakışması.")


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(customer_id: int, data: CustomerUpdate):
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")

            current = dict(row)
            updates = data.model_dump(exclude_none=True)
            for key, value in updates.items():
                current[key] = value

            conn.execute(
                """UPDATE customers SET
                   first_name=?, last_name=?, phone_number=?, email=?, region_id=?
                   WHERE customer_id=?""",
                (current["first_name"], current["last_name"],
                 current["phone_number"], current["email"],
                 current["region_id"], customer_id),
            )
            return current
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=409, detail=f"Veri çakışması: {e}")


@router.delete("/{customer_id}", status_code=204)
def delete_customer(customer_id: int):
    with get_connection() as conn:
        result = conn.execute(
            "DELETE FROM customers WHERE customer_id = ?", (customer_id,)
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")


@router.get("/{customer_id}/debt")
def get_customer_debt(customer_id: int):
    """FUNCTION: fn_get_customer_debt SQL fonksiyonu olarak çağrılır (SQLite create_function ile kayıtlı)."""
    with get_connection() as conn:
        if not conn.execute(
            "SELECT customer_id FROM customers WHERE customer_id = ?", (customer_id,)
        ).fetchone():
            raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")
        row = conn.execute(
            "SELECT fn_get_customer_debt(?) AS debt", (customer_id,)
        ).fetchone()
        return {"customer_id": customer_id, "total_unpaid_debt": row["debt"]}


@router.get("/{customer_id}/subscriptions", response_model=list[SubscriptionResponse])
def get_customer_subscriptions(customer_id: int):
    with get_connection() as conn:
        exists = conn.execute(
            "SELECT customer_id FROM customers WHERE customer_id = ?", (customer_id,)
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")

        rows = conn.execute(
            """SELECT s.subscription_id, s.customer_id, s.package_id,
                      p.package_name, s.price_at_purchase, s.status, s.started_at,
                      s.start_date, s.end_date
               FROM subscriptions s
               JOIN packages p ON s.package_id = p.package_id
               WHERE s.customer_id = ?
               ORDER BY s.started_at DESC""",
            (customer_id,),
        ).fetchall()
        return [dict(r) for r in rows]
