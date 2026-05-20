from fastapi import APIRouter, HTTPException, Query
from app.database import get_connection, sp_process_payment
from app.models import InvoiceCreate, InvoiceUpdate, InvoiceResponse, ProcessPaymentRequest

router = APIRouter(prefix="/invoices", tags=["Faturalar"])


@router.get("/", response_model=list[InvoiceResponse])
def list_invoices(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = None,
    subscription_id: int | None = None,
):
    query = "SELECT * FROM invoices WHERE 1=1"
    params: list = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if subscription_id:
        query += " AND subscription_id = ?"
        params.append(subscription_id)
    query += " ORDER BY due_date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM invoices WHERE invoice_id = ?", (invoice_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fatura bulunamadı.")
        return dict(row)


@router.post("/", response_model=InvoiceResponse, status_code=201)
def create_invoice(data: InvoiceCreate):
    with get_connection() as conn:
        sub = conn.execute(
            "SELECT subscription_id FROM subscriptions WHERE subscription_id = ?",
            (data.subscription_id,),
        ).fetchone()
        if not sub:
            raise HTTPException(status_code=404, detail="Abonelik bulunamadı.")

        cursor = conn.execute(
            "INSERT INTO invoices (subscription_id, amount, due_date, status) VALUES (?, ?, ?, ?)",
            (data.subscription_id, data.amount, str(data.due_date), data.status or "Unpaid"),
        )
        row = conn.execute(
            "SELECT * FROM invoices WHERE invoice_id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice_status(invoice_id: int, data: InvoiceUpdate):
    with get_connection() as conn:
        result = conn.execute(
            "UPDATE invoices SET status = ? WHERE invoice_id = ?",
            (data.status, invoice_id),
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Fatura bulunamadı.")
        row = conn.execute(
            "SELECT * FROM invoices WHERE invoice_id = ?", (invoice_id,)
        ).fetchone()
        return dict(row)


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(invoice_id: int):
    with get_connection() as conn:
        result = conn.execute(
            "DELETE FROM invoices WHERE invoice_id = ?", (invoice_id,)
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Fatura bulunamadı.")


@router.post("/{invoice_id}/pay")
def pay_invoice(invoice_id: int, data: ProcessPaymentRequest):
    """
    Stored Procedure: Fatura ödemesini atomik transaction ile işler.
    Ödeme kaydı eklenir, fatura 'Paid' yapılır, gelir logu güncellenir.
    Hata olursa tüm işlem otomatik ROLLBACK olur.
    """
    try:
        with get_connection() as conn:
            result = sp_process_payment(conn, invoice_id, data.amount, data.payment_method)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
