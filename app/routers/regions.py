import sqlite3
from fastapi import APIRouter, HTTPException
from app.database import get_connection
from app.models import RegionCreate, RegionResponse

router = APIRouter(prefix="/regions", tags=["Bölgeler"])


@router.get("/", response_model=list[RegionResponse])
def list_regions():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM regions ORDER BY region_name").fetchall()
        return [dict(r) for r in rows]


@router.get("/{region_id}", response_model=RegionResponse)
def get_region(region_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM regions WHERE region_id = ?", (region_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Bölge bulunamadı.")
        return dict(row)


@router.post("/", response_model=RegionResponse, status_code=201)
def create_region(data: RegionCreate):
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO regions (region_name, code) VALUES (?, ?)",
                (data.region_name, data.code),
            )
            row = conn.execute(
                "SELECT * FROM regions WHERE region_id = ?", (cursor.lastrowid,)
            ).fetchone()
            return dict(row)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Bu bölge adı veya kodu zaten mevcut.")


@router.delete("/{region_id}", status_code=204)
def delete_region(region_id: int):
    with get_connection() as conn:
        result = conn.execute(
            "DELETE FROM regions WHERE region_id = ?", (region_id,)
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Bölge bulunamadı.")
