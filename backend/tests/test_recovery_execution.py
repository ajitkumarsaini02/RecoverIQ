import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import Transaction, Customer
from tests.conftest import TestSession

@pytest.mark.asyncio
async def test_recovery_execution_retry_success():
    """Test successful recovery execution for temporary UPI failure."""
    db = TestSession()
    # Create test customer and transaction
    cust = Customer(
        id="cust_recov_1",
        name="Anika Sharma",
        email="anika@gmail.com",
        phone="+919876543210",
        lifetime_value=25000.0,
        successful_payments_count=5,
        failed_payments_count=1,
        risk_score=0.1
    )
    txn = Transaction(
        id="txn_recov_retry",
        customer_id=cust.id,
        amount=4999.0,
        currency="INR",
        status="FAILED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        customer_lifetime_value=25000.0,
        previous_successful_payments=5,
        previous_failed_payments=1,
        retry_count=0,
        max_retries=2
    )
    db.add(cust)
    db.add(txn)
    db.commit()
    db.close()

    client = TestClient(app)
    res = client.post("/api/recovery/execute/txn_recov_retry")
    assert res.status_code == 200
    data = res.json()
    assert data["transaction_id"] == "txn_recov_retry"
    if data.get("mode") == "TEST_MODE":
        assert data["status"] == "PENDING"
        assert data["amount_recovered"] == 0.0
    else:
        assert data["status"] == "SUCCESS"
        assert data["amount_recovered"] == 4999.0
    assert "timestamp" in data
    assert data["mode"] in ["TEST_MODE", "SIMULATION_MODE"]

@pytest.mark.asyncio
async def test_recovery_execution_payment_link():
    """Test payment link recovery action."""
    db = TestSession()
    cust = Customer(
        id="cust_recov_2",
        name="Karan Patel",
        email="karan@enterprise.in",
        phone="+919876543211",
        lifetime_value=15000.0,
        successful_payments_count=2,
        failed_payments_count=1,
        risk_score=0.2
    )
    txn = Transaction(
        id="txn_recov_plink",
        customer_id=cust.id,
        amount=14999.0,
        currency="INR",
        status="FAILED",
        payment_method="NETBANKING",
        failure_reason="INSUFFICIENT_FUNDS",
        retry_count=0
    )
    db.add(cust)
    db.add(txn)
    db.commit()
    db.close()

    client = TestClient(app)
    res = client.post("/api/recovery/execute/txn_recov_plink")
    assert res.status_code == 200
    data = res.json()
    assert data["action"] == "PAYMENT_LINK"
    assert data["status"] == "PENDING"
    assert "payment_link" in data["details"]

@pytest.mark.asyncio
async def test_recovery_execution_high_value_gated():
    """Test that high-value transactions return REQUIRES_APPROVAL status."""
    db = TestSession()
    cust = Customer(
        id="cust_recov_3",
        name="Dr. Sameer Saxena",
        email="sameer@medical.in",
        phone="+919876543212",
        lifetime_value=99000.0,
        successful_payments_count=4,
        failed_payments_count=1,
        risk_score=0.1
    )
    txn = Transaction(
        id="txn_recov_hv",
        customer_id=cust.id,
        amount=49999.0, # Exceeds ₹20,000
        currency="INR",
        status="FAILED",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        retry_count=0
    )
    db.add(cust)
    db.add(txn)
    db.commit()
    db.close()

    client = TestClient(app)
    res = client.post("/api/recovery/execute/txn_recov_hv")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "REQUIRES_APPROVAL"
    assert data["amount_recovered"] == 0.0
    assert data["details"]["requires_human_approval"] is True

@pytest.mark.asyncio
async def test_recovery_execution_stop_condition():
    """Test that repeated failures result in STOPPED status."""
    db = TestSession()
    txn = Transaction(
        id="txn_recov_stop",
        customer_id="cust_recov_1",
        amount=4999.0,
        currency="INR",
        status="FAILED",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        previous_failed_payments=4,
        retry_count=2, # Cap reached
        max_retries=2
    )
    db.add(txn)
    db.commit()
    db.close()

    client = TestClient(app)
    res = client.post("/api/recovery/execute/txn_recov_stop")
    assert res.status_code == 200
    data = res.json()
    assert data["action"] == "STOP"
    assert data["status"] == "STOPPED"
    assert data["amount_recovered"] == 0.0

def test_recovery_execution_not_found():
    """Test 404 handling on invalid transaction ID."""
    client = TestClient(app)
    res = client.post("/api/recovery/execute/txn_does_not_exist_999")
    assert res.status_code == 404
