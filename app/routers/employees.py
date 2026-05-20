from fastapi import APIRouter, HTTPException
from app.database import get_connection
from app.models import EmployeeCreate, EmployeeResponse

router = APIRouter(prefix="/employees", tags=["Çalışanlar"])


@router.get("/", response_model=list[EmployeeResponse])
def list_employees():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM employees ORDER BY last_name, first_name"
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(employee_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM employees WHERE employee_id = ?", (employee_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Çalışan bulunamadı.")
        return dict(row)


@router.post("/", response_model=EmployeeResponse, status_code=201)
def create_employee(data: EmployeeCreate):
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO employees (first_name, last_name, title) VALUES (?, ?, ?)",
            (data.first_name, data.last_name, data.title),
        )
        row = conn.execute(
            "SELECT * FROM employees WHERE employee_id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)


@router.delete("/{employee_id}", status_code=204)
def delete_employee(employee_id: int):
    with get_connection() as conn:
        result = conn.execute(
            "DELETE FROM employees WHERE employee_id = ?", (employee_id,)
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Çalışan bulunamadı.")
