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
    r = client.post("/regions/", json={"region_name": "Marmara", "code": "MRM"})
    assert r.status_code == 201
    data = r.json()
    assert data["region_name"] == "Marmara"
    assert data["code"] == "MRM"

    r2 = client.get(f"/regions/{data['region_id']}")
    assert r2.status_code == 200


def test_create_duplicate_region_returns_409():
    client.post("/regions/", json={"region_name": "Ege", "code": "EGE"})
    r = client.post("/regions/", json={"region_name": "Ege", "code": "EGE"})
    assert r.status_code == 409


def test_create_region_duplicate_code_returns_409():
    client.post("/regions/", json={"region_name": "Bölge A", "code": "BA"})
    r = client.post("/regions/", json={"region_name": "Bölge B", "code": "BA"})
    assert r.status_code == 409


def test_get_nonexistent_region_returns_404():
    r = client.get("/regions/9999")
    assert r.status_code == 404


# ────────────────────────── PACKAGES ──────────────────────────

def test_create_package():
    r = client.post("/packages/", json={"package_name": "Test Paket", "monthly_fee": 99.9, "speed_mbps": 50})
    assert r.status_code == 201
    assert r.json()["package_name"] == "Test Paket"
    assert r.json()["speed_mbps"] == 50
    assert r.json()["quota_gb"] is None  # sınırsız


def test_create_package_with_quota():
    r = client.post("/packages/", json={"package_name": "Kotali Paket", "monthly_fee": 70.0, "speed_mbps": 25, "quota_gb": 10})
    assert r.status_code == 201
    assert r.json()["quota_gb"] == 10


def test_create_package_negative_fee_returns_422():
    r = client.post("/packages/", json={"package_name": "Kötü Paket", "monthly_fee": -10, "speed_mbps": 50})
    assert r.status_code == 422


def test_create_package_missing_speed_returns_422():
    r = client.post("/packages/", json={"package_name": "Eksik Paket", "monthly_fee": 100.0})
    assert r.status_code == 422


def test_update_package():
    r = client.post("/packages/", json={"package_name": "Eski Ad", "monthly_fee": 100.0, "speed_mbps": 25})
    pid = r.json()["package_id"]

    r2 = client.patch(f"/packages/{pid}", json={"monthly_fee": 200.0, "speed_mbps": 100})
    assert r2.status_code == 200
    assert r2.json()["monthly_fee"] == 200.0
    assert r2.json()["speed_mbps"] == 100


# ────────────────────────── CUSTOMERS ──────────────────────────

def _create_region():
    r = client.post("/regions/", json={"region_name": "Test Bölge", "code": "TST"})
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
    p = client.post("/packages/", json={"package_name": "Test", "monthly_fee": 100.0, "speed_mbps": 50}).json()
    return c["customer_id"], p["package_id"]


def test_create_subscription():
    c_id, p_id = _setup_subscription()
    r = client.post("/subscriptions/", json={"customer_id": c_id, "package_id": p_id})
    assert r.status_code == 201
    assert r.json()["status"] == "active"


def test_create_subscription_with_dates():
    c_id, p_id = _setup_subscription()
    r = client.post("/subscriptions/", json={
        "customer_id": c_id, "package_id": p_id,
        "start_date": "2026-01-01", "end_date": "2026-12-31",
    })
    assert r.status_code == 201


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
    p = client.post("/packages/", json={"package_name": "Test", "monthly_fee": 100.0, "speed_mbps": 50}).json()
    r = client.post("/subscriptions/", json={"customer_id": 9999, "package_id": p["package_id"]})
    assert r.status_code == 404


def test_stats_by_package():
    r = client.get("/subscriptions/stats/by-package")
    assert r.status_code == 200


def test_stats_by_region():
    r = client.get("/subscriptions/stats/by-region")
    assert r.status_code == 200


# ────────────────────────── EMPLOYEES ──────────────────────────

def _create_employee():
    return client.post("/employees/", json={
        "first_name": "Ahmet",
        "last_name": "Çelik",
        "title": "Destek Elemanı",
    })


def test_create_employee():
    r = _create_employee()
    assert r.status_code == 201
    assert r.json()["first_name"] == "Ahmet"
    assert r.json()["title"] == "Destek Elemanı"


def test_list_employees():
    _create_employee()
    r = client.get("/employees/")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_get_employee():
    e = _create_employee().json()
    r = client.get(f"/employees/{e['employee_id']}")
    assert r.status_code == 200
    assert r.json()["employee_id"] == e["employee_id"]


def test_get_nonexistent_employee_returns_404():
    r = client.get("/employees/9999")
    assert r.status_code == 404


def test_delete_employee():
    e = _create_employee().json()
    r = client.delete(f"/employees/{e['employee_id']}")
    assert r.status_code == 204
    assert client.get(f"/employees/{e['employee_id']}").status_code == 404


# ────────────────────────── INVOICES ──────────────────────────

def _setup_invoice():
    c_id, p_id = _setup_subscription()
    s = client.post("/subscriptions/", json={"customer_id": c_id, "package_id": p_id}).json()
    return s["subscription_id"]


def test_create_invoice():
    sub_id = _setup_invoice()
    r = client.post("/invoices/", json={
        "subscription_id": sub_id,
        "amount": 150.0,
        "due_date": "2026-06-01",
    })
    assert r.status_code == 201
    assert r.json()["status"] == "Unpaid"
    assert r.json()["amount"] == 150.0


def test_create_invoice_invalid_subscription_returns_404():
    r = client.post("/invoices/", json={
        "subscription_id": 9999,
        "amount": 100.0,
        "due_date": "2026-06-01",
    })
    assert r.status_code == 404


def test_list_invoices():
    sub_id = _setup_invoice()
    client.post("/invoices/", json={"subscription_id": sub_id, "amount": 100.0, "due_date": "2026-06-01"})
    r = client.get("/invoices/")
    assert r.status_code == 200


def test_get_invoice():
    sub_id = _setup_invoice()
    inv = client.post("/invoices/", json={
        "subscription_id": sub_id, "amount": 200.0, "due_date": "2026-06-01"
    }).json()
    r = client.get(f"/invoices/{inv['invoice_id']}")
    assert r.status_code == 200
    assert r.json()["amount"] == 200.0


def test_update_invoice_status():
    sub_id = _setup_invoice()
    inv = client.post("/invoices/", json={
        "subscription_id": sub_id, "amount": 100.0, "due_date": "2026-06-01"
    }).json()
    r = client.patch(f"/invoices/{inv['invoice_id']}", json={"status": "Overdue"})
    assert r.status_code == 200
    assert r.json()["status"] == "Overdue"


def test_delete_invoice():
    sub_id = _setup_invoice()
    inv = client.post("/invoices/", json={
        "subscription_id": sub_id, "amount": 100.0, "due_date": "2026-06-01"
    }).json()
    r = client.delete(f"/invoices/{inv['invoice_id']}")
    assert r.status_code == 204


# ────────────────────────── STORED PROCEDURE: pay_invoice ──────────────────────────

def test_pay_invoice_stored_procedure():
    """sp_process_payment: ödeme kaydı + fatura Paid + revenue log — hepsi tek transaction."""
    sub_id = _setup_invoice()
    inv = client.post("/invoices/", json={
        "subscription_id": sub_id, "amount": 300.0, "due_date": "2026-06-01"
    }).json()

    r = client.post(f"/invoices/{inv['invoice_id']}/pay", json={
        "amount": 300.0,
        "payment_method": "Credit Card",
    })
    assert r.status_code == 200
    assert r.json()["status"] == "Paid"

    # Fatura gerçekten Paid mi?
    inv_check = client.get(f"/invoices/{inv['invoice_id']}").json()
    assert inv_check["status"] == "Paid"

    # Ödeme kaydı oluştu mu?
    payments = client.get(f"/payments/?invoice_id={inv['invoice_id']}").json()
    assert len(payments) == 1
    assert payments[0]["amount"] == 300.0


def test_pay_nonexistent_invoice_returns_404():
    r = client.post("/invoices/9999/pay", json={
        "amount": 100.0,
        "payment_method": "Bank Transfer",
    })
    assert r.status_code == 404


# ────────────────────────── PAYMENTS ──────────────────────────

def test_list_payments():
    r = client.get("/payments/")
    assert r.status_code == 200


def test_get_nonexistent_payment_returns_404():
    r = client.get("/payments/9999")
    assert r.status_code == 404


# ────────────────────────── SUPPORT TICKETS ──────────────────────────

def test_create_support_ticket():
    c = _create_customer().json()
    e = _create_employee().json()
    r = client.post("/support-tickets/", json={
        "customer_id": c["customer_id"],
        "employee_id": e["employee_id"],
        "subject": "Modem arızası",
        "description": "Modem yanmış olabilir.",
    })
    assert r.status_code == 201
    assert r.json()["status"] == "Open"
    assert r.json()["subject"] == "Modem arızası"


def test_create_ticket_invalid_customer_returns_404():
    r = client.post("/support-tickets/", json={
        "customer_id": 9999,
        "subject": "Test",
    })
    assert r.status_code == 404


def test_list_support_tickets():
    r = client.get("/support-tickets/")
    assert r.status_code == 200


def test_update_ticket_status():
    c = _create_customer().json()
    t = client.post("/support-tickets/", json={
        "customer_id": c["customer_id"],
        "subject": "Yavaş internet",
    }).json()
    r = client.patch(f"/support-tickets/{t['ticket_id']}", json={"status": "Resolved"})
    assert r.status_code == 200
    assert r.json()["status"] == "Resolved"


def test_delete_support_ticket():
    c = _create_customer().json()
    t = client.post("/support-tickets/", json={
        "customer_id": c["customer_id"],
        "subject": "Fatura sorunu",
    }).json()
    r = client.delete(f"/support-tickets/{t['ticket_id']}")
    assert r.status_code == 204


# ────────────────────────── VIEW: customer_dashboard ──────────────────────────

def test_customer_dashboard_view():
    r = client.get("/customers/dashboard")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ────────────────────────── FUNCTION: customer_debt ──────────────────────────

def test_customer_debt_function_zero():
    c = _create_customer().json()
    r = client.get(f"/customers/{c['customer_id']}/debt")
    assert r.status_code == 200
    assert r.json()["total_unpaid_debt"] == 0.0


def test_customer_debt_function_with_invoice():
    c_id, p_id = _setup_subscription()
    s = client.post("/subscriptions/", json={"customer_id": c_id, "package_id": p_id}).json()
    client.post("/invoices/", json={
        "subscription_id": s["subscription_id"],
        "amount": 250.0,
        "due_date": "2026-06-01",
    })
    r = client.get(f"/customers/{c_id}/debt")
    assert r.status_code == 200
    assert r.json()["total_unpaid_debt"] == 250.0


def test_customer_debt_nonexistent_returns_404():
    r = client.get("/customers/9999/debt")
    assert r.status_code == 404


# ────────────────────────── TRIGGER: customer_logs ──────────────────────────

def test_trigger_logs_on_customer_update():
    """trg_customer_audit_update: güncelleme sonrası customer_logs'a JSON formatında kayıt düşmeli."""
    from app.database import get_connection
    import json
    c = _create_customer().json()
    client.patch(f"/customers/{c['customer_id']}", json={"first_name": "Mehmet"})

    with get_connection() as conn:
        log = conn.execute(
            "SELECT * FROM customer_logs WHERE customer_id = ? AND action_type = 'UPDATE'",
            (c["customer_id"],),
        ).fetchone()
    assert log is not None
    # old_data ve new_data geçerli JSON olmalı
    old = json.loads(log["old_data"])
    new = json.loads(log["new_data"])
    assert old["first_name"] == "Ahmet"
    assert new["first_name"] == "Mehmet"
    assert old["customer_id"] == c["customer_id"]


def test_trigger_logs_on_customer_delete():
    """trg_customer_audit_delete: silme sonrası customer_logs'a JSON formatında kayıt düşmeli."""
    from app.database import get_connection
    import json
    c = _create_customer().json()
    client.delete(f"/customers/{c['customer_id']}")

    with get_connection() as conn:
        log = conn.execute(
            "SELECT * FROM customer_logs WHERE customer_id = ? AND action_type = 'DELETE'",
            (c["customer_id"],),
        ).fetchone()
    assert log is not None
    old = json.loads(log["old_data"])
    assert old["customer_id"] == c["customer_id"]
    assert log["new_data"] is None
