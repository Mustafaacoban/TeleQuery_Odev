import sqlite3
from fastapi import APIRouter, HTTPException
from app.database import get_connection
from app.models import PackageCreate, PackageUpdate, PackageResponse

router = APIRouter(prefix="/packages", tags=["Paketler"])


@router.get("/", response_model=list[PackageResponse])
def list_packages():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM packages ORDER BY monthly_fee").fetchall()
        return [dict(r) for r in rows]


@router.get("/{package_id}", response_model=PackageResponse)
def get_package(package_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM packages WHERE package_id = ?", (package_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Paket bulunamadı.")
        return dict(row)


@router.post("/", response_model=PackageResponse, status_code=201)
def create_package(data: PackageCreate):
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO packages (package_name, monthly_fee, speed_mbps, quota_gb) VALUES (?, ?, ?, ?)",
            (data.package_name, data.monthly_fee, data.speed_mbps, data.quota_gb),
        )
        row = conn.execute(
            "SELECT * FROM packages WHERE package_id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)


@router.patch("/{package_id}", response_model=PackageResponse)
def update_package(package_id: int, data: PackageUpdate):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM packages WHERE package_id = ?", (package_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Paket bulunamadı.")

        updated = dict(row)
        updated.update(data.model_dump(exclude_unset=True))

        conn.execute(
            "UPDATE packages SET package_name=?, monthly_fee=?, speed_mbps=?, quota_gb=? WHERE package_id=?",
            (updated["package_name"], updated["monthly_fee"],
             updated["speed_mbps"], updated.get("quota_gb"), package_id),
        )
        return updated


@router.delete("/{package_id}", status_code=204)
def delete_package(package_id: int):
    with get_connection() as conn:
        result = conn.execute(
            "DELETE FROM packages WHERE package_id = ?", (package_id,)
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Paket bulunamadı.")
