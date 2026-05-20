from fastapi import APIRouter, HTTPException, Query
from app.database import get_connection
from app.models import PaymentResponse

router = APIRouter(prefix="/payments", tags=["Ödemeler"])


@router.get("/", response_model=list[PaymentResponse])
def list_payments(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    invoice_id: int | None = None,
):
    query = "SELECT * FROM payments WHERE 1=1"
    params: list = []
    if invoice_id:
        query += " AND invoice_id = ?"
        params.append(invoice_id)
    query += " ORDER BY payment_date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM payments WHERE payment_id = ?", (payment_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Ödeme bulunamadı.")
        return dict(row)
