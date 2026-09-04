import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.razorpay_service import razorpay_service
from app.services.ai_agent import ai_agent
from app.services.policy_engine import policy_engine
from app.db.models import Transaction, Customer

@pytest.mark.asyncio
async def test_razorpay_service_abstraction():
    # Test order creation in simulation/fallback mode
    order = await razorpay_service.create_order(amount_in_inr=4999.0)
    assert order is not None
    assert "id" in order
    assert order["amount"] == 499900 # In paise
    assert order["currency"] == "INR"
    assert order["mode"] in ["TEST_MODE", "SIMULATION_MODE"]

    # Test payment link creation
    plink = await razorpay_service.create_payment_link(
        amount_in_inr=4999.0,
        customer_name="Priya Sharma",
        customer_email="priya.sharma@gmail.com"
    )
    assert plink is not None
    assert "short_url" in plink

def test_ai_agent_and_policy_engine_temporary_upi_failure():
    # Scenario 1: ₹4,999 UPI Timeout with high LTV customer
    cust = Customer(
        id="cust_test_1",
        name="Priya Sharma",
        email="priya.sharma@gmail.com",
        phone="+919876543210",
        lifetime_value=39992.0,
        successful_payments_count=8,
        failed_payments_count=1,
        risk_score=0.08
    )
    txn = Transaction(
        id="txn_test_1",
        customer_id=cust.id,
        amount=4999.0,
        currency="INR",
        status="FAILED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        customer_lifetime_value=39992.0,
        previous_successful_payments=8,
        previous_failed_payments=1,
        previous_recovery_attempts=0,
        retry_count=0
    )

    ai_rec = ai_agent.analyze_failure(transaction=txn, customer=cust)
    assert ai_rec.recommended_action == "RETRY_PAYMENT"
    assert ai_rec.recovery_probability >= 0.85
    assert ai_rec.risk_level == "LOW"

    policy_res = policy_engine.evaluate(transaction=txn, recommendation=ai_rec)
    assert policy_res.allowed is True
    assert policy_res.action == "RETRY_PAYMENT"
    assert policy_res.requires_human_approval is False

def test_policy_engine_max_retries_and_high_value_gate():
    # Case A: Retry count = 2 -> Should force STOP
    txn_max_retries = Transaction(
        id="txn_test_2",
        customer_id="cust_test_2",
        amount=4999.0,
        currency="INR",
        status="FAILED",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        retry_count=2,
        max_retries=2
    )
    ai_rec = ai_agent.analyze_failure(transaction=txn_max_retries)
    policy_res = policy_engine.evaluate(transaction=txn_max_retries, recommendation=ai_rec)
    assert policy_res.allowed is False
    assert policy_res.action == "STOP"

    # Case B: High Value Amount = ₹49,999 -> Requires Human Approval
    txn_high_value = Transaction(
        id="txn_test_3",
        customer_id="cust_test_3",
        amount=49999.0,
        currency="INR",
        status="FAILED",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        retry_count=0,
        max_retries=2
    )
    ai_rec_hv = ai_agent.analyze_failure(transaction=txn_high_value)
    policy_res_hv = policy_engine.evaluate(transaction=txn_high_value, recommendation=ai_rec_hv)
    assert policy_res_hv.requires_human_approval is True

def test_api_demo_scenario_endpoint():
    client = TestClient(app)
    response = client.post("/api/demo/scenario", json={"scenario": "temporary_upi_failure", "mode": "SIMULATION_MODE"})
    assert response.status_code == 200
    data = response.json()
    assert data["scenario_id"] == "temporary_upi_failure"
    assert data["transaction"]["amount"] == 4999.0
    assert data["ai_analysis"]["recommended_action"] == "RETRY_PAYMENT"
    assert data["policy_decision"]["action"] == "RETRY_PAYMENT"
    assert data["recovery_result"]["status"] == "SUCCESS"
    assert data["recovery_result"]["recovered_amount"] == 4999.0
    assert len(data["audit_timeline"]) >= 3

def test_api_demo_high_value_approval_flow():
    client = TestClient(app)
    # 1. Run high-value scenario in SIMULATION_MODE
    response = client.post("/api/demo/scenario", json={"scenario": "high_value_transaction", "mode": "SIMULATION_MODE"})
    assert response.status_code == 200
    data = response.json()
    assert data["policy_decision"]["requires_human_approval"] is True
    assert data["transaction"]["status"] == "APPROVAL_REQUIRED"

    # 2. Check approval queue
    approvals_res = client.get("/api/approvals")
    assert approvals_res.status_code == 200
    approvals = approvals_res.json()
    assert len(approvals) >= 1
    action_id = approvals[0]["id"]

    # 3. Approve action
    approve_res = client.post(f"/api/recovery/approve/{action_id}")
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED_AND_EXECUTED"

def test_api_dashboard_and_simulation():
    client = TestClient(app)
    # Run a scenario first so we have data
    client.post("/api/demo/scenario", json={"scenario": "temporary_upi_failure", "mode": "SIMULATION_MODE"})
    
    # Check dashboard metrics
    metrics_res = client.get("/api/dashboard")
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    assert "revenue_at_risk" in metrics
    assert "revenue_recovered" in metrics
    assert metrics["successful_recoveries_count"] >= 1

    # Run batch simulation
    sim_res = client.post("/api/simulation/run")
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert "simulation_id" in sim_data
    assert "revenue_recovered" in sim_data
    assert "recovery_rate" in sim_data
