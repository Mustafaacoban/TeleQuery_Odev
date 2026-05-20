from fastapi import APIRouter, HTTPException, Query
from app.database import get_connection
from app.models import SupportTicketCreate, SupportTicketUpdate, SupportTicketResponse

router = APIRouter(prefix="/support-tickets", tags=["Destek Talepleri"])


@router.get("/", response_model=list[SupportTicketResponse])
def list_tickets(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = None,
    customer_id: int | None = None,
):
    query = "SELECT * FROM support_tickets WHERE 1=1"
    params: list = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if customer_id:
        query += " AND customer_id = ?"
        params.append(customer_id)
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


@router.get("/{ticket_id}", response_model=SupportTicketResponse)
def get_ticket(ticket_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM support_tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Destek talebi bulunamadı.")
        return dict(row)


@router.post("/", response_model=SupportTicketResponse, status_code=201)
def create_ticket(data: SupportTicketCreate):
    with get_connection() as conn:
        if not conn.execute(
            "SELECT customer_id FROM customers WHERE customer_id = ?", (data.customer_id,)
        ).fetchone():
            raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")

        if data.employee_id and not conn.execute(
            "SELECT employee_id FROM employees WHERE employee_id = ?", (data.employee_id,)
        ).fetchone():
            raise HTTPException(status_code=404, detail="Çalışan bulunamadı.")

        cursor = conn.execute(
            """INSERT INTO support_tickets
               (customer_id, employee_id, subject, description, status)
               VALUES (?, ?, ?, ?, ?)""",
            (data.customer_id, data.employee_id, data.subject,
             data.description, data.status or "Open"),
        )
        row = conn.execute(
            "SELECT * FROM support_tickets WHERE ticket_id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)


@router.patch("/{ticket_id}", response_model=SupportTicketResponse)
def update_ticket(ticket_id: int, data: SupportTicketUpdate):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM support_tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Destek talebi bulunamadı.")

        current = dict(row)
        if data.status is not None:
            current["status"] = data.status
        if data.employee_id is not None:
            current["employee_id"] = data.employee_id

        conn.execute(
            "UPDATE support_tickets SET status = ?, employee_id = ? WHERE ticket_id = ?",
            (current["status"], current["employee_id"], ticket_id),
        )
        return current


@router.delete("/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: int):
    with get_connection() as conn:
        result = conn.execute(
            "DELETE FROM support_tickets WHERE ticket_id = ?", (ticket_id,)
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Destek talebi bulunamadı.")
