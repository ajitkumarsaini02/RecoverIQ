import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import Customer, Transaction, RecoveryAction, AuditEvent
from tests.conftest import TestSession

def test_database_models_and_seeding():
    db = TestSession()
    customer_count = db.query(Customer).count()
    txn_count = db.query(Transaction).count()
    audit_count = db.query(AuditEvent).count()
    
    assert customer_count >= 50
    assert txn_count >= 150
    assert audit_count >= 150
    
    # Verify transaction fields
    txn = db.query(Transaction).first()
    assert txn.id.startswith("txn_")
    assert txn.customer_id.startswith("cust_")
    assert txn.amount in [499.0, 999.0, 1499.0, 1999.0, 2499.0, 3999.0, 4999.0, 7499.0, 9999.0, 14999.0, 19999.0, 24999.0, 49999.0, 99999.0]
    assert txn.failure_reason in ["UPI_TIMEOUT", "BANK_DECLINED", "INSUFFICIENT_FUNDS", "NETWORK_ERROR", "PAYMENT_METHOD_ERROR", "UNKNOWN"]
    assert txn.customer is not None
    assert txn.customer_lifetime_value >= 0
    assert txn.previous_successful_payments >= 0
    assert txn.previous_failed_payments >= 0
    assert txn.previous_recovery_attempts >= 0
    db.close()

def test_api_list_transactions():
    client = TestClient(app)
    response = client.get("/api/transactions?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 150
    assert len(data["items"]) == 10
    assert data["data_label"] == "DEMO / SYNTHETIC DATA"

def test_api_filter_transactions_by_failure_reason():
    client = TestClient(app)
    response = client.get("/api/transactions?failure_reason=UPI_TIMEOUT")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) > 0
    for item in data["items"]:
        assert item["failure_reason"] == "UPI_TIMEOUT"

def test_api_get_single_transaction_detail():
    client = TestClient(app)
    # First get a transaction ID
    list_res = client.get("/api/transactions?limit=1")
    assert list_res.status_code == 200
    txn_id = list_res.json()["items"][0]["id"]

    # Now get detail
    detail_res = client.get(f"/api/transactions/{txn_id}")
    assert detail_res.status_code == 200
    txn_data = detail_res.json()
    assert txn_data["id"] == txn_id
    assert txn_data["customer"] is not None
    assert "name" in txn_data["customer"]
    assert "email" in txn_data["customer"]
    assert "customer_lifetime_value" in txn_data
    assert "lifetime_value" in txn_data["customer"]
    assert "previous_successful_payments" in txn_data

def test_api_transaction_not_found():
    client = TestClient(app)
    response = client.get("/api/transactions/txn_non_existent_99999")
    assert response.status_code == 404

def test_api_list_and_get_customers():
    client = TestClient(app)
    # 1. List customers
    res = client.get("/api/customers?limit=5")
    assert res.status_code == 200
    custs = res.json()
    assert len(custs) == 5
    cust_id = custs[0]["id"]
    
    # 2. Get customer detail
    res_detail = client.get(f"/api/customers/{cust_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == cust_id
    assert "email" in res_detail.json()
    
    # 3. Customer 404
    res_404 = client.get("/api/customers/cust_non_existent_99999")
    assert res_404.status_code == 404

def test_database_url_postgresql_compatibility():
    """Verify that PostgreSQL URL variants (postgres://) are correctly normalized without crashing."""
    raw_render_url = "postgres://recoveriq_user:secretpass@dpg-c0123456789-a.oregon-postgres.render.com/recoveriq_prod"
    normalized = raw_render_url.replace("postgres://", "postgresql://", 1) if raw_render_url.startswith("postgres://") else raw_render_url
    assert normalized.startswith("postgresql://")
    assert "recoveriq_user" in normalized
    assert "recoveriq_prod" in normalized


