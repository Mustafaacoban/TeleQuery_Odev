import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, get_connection

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    """Her test için temiz, izole bir veritabanı."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_URL", db_path)

    import app.database as db_module
    monkeypatch.setattr(db_module, "DB_NAME", db_path)

    init_db(db_path)
    yield


# ────────────────────────── REGIONS ──────────────────────────

def test_list_regions_empty():
    r = client.get("/regions/")
    assert r.status_code == 200
    assert r.json() == []


def test_create_and_get_region():
    r = client.post("/regions/", json={"region_name": "Marmara"})
    assert r.status_code == 201
    data = r.json()
    assert data["region_name"] == "Marmara"

    r2 = client.get(f"/regions/{data['region_id']}")
    assert r2.status_code == 200


def test_create_duplicate_region_returns_409():
    client.post("/regions/", json={"region_name": "Ege"})
    r = client.post("/regions/", json={"region_name": "Ege"})
    assert r.status_code == 409


def test_get_nonexistent_region_returns_404():
    r = client.get("/regions/9999")
    assert r.status_code == 404


# ────────────────────────── PACKAGES ──────────────────────────

def test_create_package():
    r = client.post("/packages/", json={"package_name": "Test Paket", "monthly_fee": 99.9})
    assert r.status_code == 201
    assert r.json()["package_name"] == "Test Paket"


def test_create_package_negative_fee_returns_422():
    r = client.post("/packages/", json={"package_name": "Kötü Paket", "monthly_fee": -10})
    assert r.status_code == 422


def test_update_package():
    r = client.post("/packages/", json={"package_name": "Eski Ad", "monthly_fee": 100.0})
    pid = r.json()["package_id"]

    r2 = client.patch(f"/packages/{pid}", json={"monthly_fee": 200.0})
    assert r2.status_code == 200
    assert r2.json()["monthly_fee"] == 200.0


# ────────────────────────── CUSTOMERS ──────────────────────────

def _create_region():
    r = client.post("/regions/", json={"region_name": "Test Bölge"})
    return r.json()["region_id"]


def _create_customer(region_id=None):
    return client.post("/customers/", json={
        "first_name": "Ahmet",
        "last_name": "Yılmaz",
        "phone_number": "05551234567",
        "email": "ahmet@test.com",
        "region_id": region_id,
    })


def test_create_customer():
    r = _create_customer()
    assert r.status_code == 201
    assert r.json()["first_name"] == "Ahmet"


def test_create_customer_invalid_email_returns_422():
    r = client.post("/customers/", json={
        "first_name": "Ali",
        "last_name": "Veli",
        "phone_number": "05551234567",
        "email": "gecersiz-email",
    })
    assert r.status_code == 422


def test_create_customer_invalid_phone_returns_422():
    r = client.post("/customers/", json={
        "first_name": "Ali",
        "last_name": "Veli",
        "phone_number": "abc",
        "email": "ali@test.com",
    })
    assert r.status_code == 422


def test_duplicate_customer_email_returns_409():
    _create_customer()
    r = _create_customer()
    assert r.status_code == 409


def test_get_customer():
    c = _create_customer().json()
    r = client.get(f"/customers/{c['customer_id']}")
    assert r.status_code == 200


def test_update_customer():
    c = _create_customer().json()
    r = client.patch(f"/customers/{c['customer_id']}", json={"first_name": "Mehmet"})
    assert r.status_code == 200
    assert r.json()["first_name"] == "Mehmet"


def test_delete_customer():
    c = _create_customer().json()
    r = client.delete(f"/customers/{c['customer_id']}")
    assert r.status_code == 204

    r2 = client.get(f"/customers/{c['customer_id']}")
    assert r2.status_code == 404


def test_get_nonexistent_customer_returns_404():
    r = client.get("/customers/99999")
    assert r.status_code == 404


# ────────────────────────── SUBSCRIPTIONS ──────────────────────────

def _setup_subscription():
    c = _create_customer().json()
    p = client.post("/packages/", json={"package_name": "Test", "monthly_fee": 100.0}).json()
    return c["customer_id"], p["package_id"]


def test_create_subscription():
    c_id, p_id = _setup_subscription()
    r = client.post("/subscriptions/", json={"customer_id": c_id, "package_id": p_id})
    assert r.status_code == 201
    assert r.json()["status"] == "active"


def test_duplicate_subscription_returns_409():
    c_id, p_id = _setup_subscription()
    client.post("/subscriptions/", json={"customer_id": c_id, "package_id": p_id})
    r = client.post("/subscriptions/", json={"customer_id": c_id, "package_id": p_id})
    assert r.status_code == 409


def test_update_subscription_status():
    c_id, p_id = _setup_subscription()
    s = client.post("/subscriptions/", json={"customer_id": c_id, "package_id": p_id}).json()
    r = client.patch(f"/subscriptions/{s['subscription_id']}", json={"status": "cancelled"})
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_invalid_subscription_status_returns_422():
    c_id, p_id = _setup_subscription()
    s = client.post("/subscriptions/", json={"customer_id": c_id, "package_id": p_id}).json()
    r = client.patch(f"/subscriptions/{s['subscription_id']}", json={"status": "gecersiz"})
    assert r.status_code == 422


def test_subscription_for_nonexistent_customer_returns_404():
    p = client.post("/packages/", json={"package_name": "Test", "monthly_fee": 100.0}).json()
    r = client.post("/subscriptions/", json={"customer_id": 9999, "package_id": p["package_id"]})
    assert r.status_code == 404


def test_stats_by_package():
    r = client.get("/subscriptions/stats/by-package")
    assert r.status_code == 200


def test_stats_by_region():
    r = client.get("/subscriptions/stats/by-region")
    assert r.status_code == 200
