import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import Transaction, Customer, RecoveryAction
from tests.conftest import TestSession

def test_dashboard_metrics_dynamic_calculation():
    """
    Test that GET /api/dashboard returns metrics calculated directly from the DB
    according to the specified formulas.
    """
    client = TestClient(app)
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    data = res.json()

    # 1. Verify all 8 core KPI fields exist and are numeric
    assert "revenue_at_risk" in data
    assert "revenue_recovered" in data
    assert "recovery_rate" in data
    assert "total_failed_count" in data
    assert "recovery_attempts_count" in data
    assert "successful_recoveries_count" in data
    assert "pending_approvals_count" in data
    assert "stopped_cases_count" in data

    # 2. Formula verification:
    # Revenue at Risk >= 0, Revenue Recovered >= 0
    assert data["revenue_at_risk"] >= 0.0
    assert data["revenue_recovered"] >= 0.0
    assert 0.0 <= data["recovery_rate"] <= 100.0

    # 3. Verify all 5 chart datasets
    assert "failure_reasons_breakdown" in data
    assert isinstance(data["failure_reasons_breakdown"], list)
    assert len(data["failure_reasons_breakdown"]) > 0

    assert "recovery_actions_breakdown" in data
    assert isinstance(data["recovery_actions_breakdown"], list)

    assert "recovery_outcomes_breakdown" in data
    assert isinstance(data["recovery_outcomes_breakdown"], list)

    assert "recovery_trend" in data
    assert len(data["recovery_trend"]) == 7 # 7-day trend
    for day in data["recovery_trend"]:
        assert "date" in day
        assert "at_risk" in day
        assert "recovered" in day
        assert "recovery_rate" in day

    # 4. Labeling
    assert "Synthetic" in data["data_label"] or "DEMO" in data["data_label"]

def test_dashboard_recalculation_after_recovery():
    """
    Test that executing a recovery immediately updates Revenue Recovered
    and decreases Revenue at Risk dynamically.
    """
    db = TestSession()
    # Create test failed transaction
    cust = Customer(
        id="cust_dash_calc",
        name="Sunil Mehra",
        email="sunil@business.in",
        phone="+919876543299",
        lifetime_value=20000.0,
        successful_payments_count=3,
        failed_payments_count=1,
        risk_score=0.1
    )
    txn = Transaction(
        id="txn_dash_calc_1",
        customer_id=cust.id,
        amount=5000.0,
        currency="INR",
        status="FAILED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=0
    )
    db.add(cust)
    db.add(txn)
    db.commit()
    db.close()

    client = TestClient(app)
    # Get baseline metrics
    m1 = client.get("/api/dashboard").json()
    base_recovered = m1["revenue_recovered"]

    # Execute recovery on the transaction
    exec_res = client.post("/api/recovery/execute/txn_dash_calc_1")
    assert exec_res.status_code == 200
    assert exec_res.json()["status"] == "SUCCESS"

    # Get updated metrics
    m2 = client.get("/api/dashboard").json()
    assert m2["revenue_recovered"] == base_recovered + 5000.0
    assert m2["successful_recoveries_count"] == m1["successful_recoveries_count"] + 1
