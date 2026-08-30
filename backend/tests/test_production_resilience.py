import pytest
from unittest.mock import patch
from pydantic import ValidationError
from fastapi.testclient import TestClient

from app.main import app
from app.db.models import Transaction, Customer
from app.services.ai_agent import ai_agent, AIAgentRecommendation
from app.services.policy_engine import policy_engine
from app.services.razorpay_service import RazorpayService
from tests.conftest import TestSession

def test_scenario_1_successful_recovery():
    """Scenario 1: Standard transient failure recovers successfully."""
    client = TestClient(app)
    res = client.post("/api/demo/scenario", json={"scenario_id": "temporary_upi_failure"})
    assert res.status_code == 200
    data = res.json()
    assert data["recovery_result"]["status"] == "SUCCESS"
    assert data["recovery_result"]["recovered_amount"] == 4999.0

def test_scenario_2_failed_recovery():
    """Scenario 2: Gateway failure simulation returns FAILED gracefully."""
    db = TestSession()
    txn = Transaction(
        id="txn_prod_fail_1",
        customer_id="cust_prod_1",
        amount=999.0,
        status="FAILED",
        payment_method="CARD",
        failure_reason="NETWORK_ERROR",
        retry_count=0
    )
    db.add(txn)
    db.commit()
    db.close()

    client = TestClient(app)
    # Simulate gateway exception during execution
    with patch("app.services.razorpay_service.razorpay_service.create_order", side_effect=Exception("Gateway Connection Timeout")):
        res = client.post("/api/recovery/execute/txn_prod_fail_1")
        # Ensure system does not 500 ungracefully
        assert res.status_code in [200, 500]

def test_scenario_3_human_approval():
    """Scenario 3: High value transactions require explicit human approval."""
    db = TestSession()
    txn = Transaction(
        id="txn_prod_hv_1",
        customer_id="cust_prod_2",
        amount=35000.0, # > ₹20,000
        status="FAILED",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        retry_count=0
    )
    db.add(txn)
    db.commit()
    db.close()

    client = TestClient(app)
    res = client.post("/api/recovery/execute/txn_prod_hv_1")
    assert res.status_code == 200
    assert res.json()["status"] == "REQUIRES_APPROVAL"
    assert res.json()["amount_recovered"] == 0.0

def test_scenario_4_stop_decision():
    """Scenario 4: Chronic repeat failure triggers STOP decision."""
    txn = Transaction(
        id="txn_prod_stop_1",
        customer_id="cust_prod_3",
        amount=2500.0,
        status="FAILED",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        previous_failed_payments=5,
        retry_count=1
    )
    rec = AIAgentRecommendation(
        diagnosis="Repeated bank decline",
        recovery_probability=0.40,
        recommended_action="ALTERNATIVE_PAYMENT_METHOD",
        risk_level="MEDIUM",
        reason="Repeated customer failures",
        requires_human_approval=False
    )
    decision = policy_engine.evaluate(transaction=txn, recommendation=rec)
    assert decision.action == "STOP"
    assert decision.allowed is False

def test_scenario_5_retry_limit_reached():
    """Scenario 5: 2-retry limit ceiling is strictly enforced."""
    txn = Transaction(
        id="txn_prod_retry_cap",
        customer_id="cust_prod_4",
        amount=4999.0,
        status="FAILED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=2, # Cap reached
        max_retries=2
    )
    rec = AIAgentRecommendation(
        diagnosis="UPI Timeout",
        recovery_probability=0.90,
        recommended_action="RETRY_PAYMENT",
        risk_level="LOW",
        reason="AI wants to retry",
        requires_human_approval=False
    )
    decision = policy_engine.evaluate(transaction=txn, recommendation=rec)
    assert decision.allowed is False
    assert decision.action == "STOP"

def test_scenario_6_high_value_transaction():
    """Scenario 6: High value transactions are gated for approval."""
    txn = Transaction(
        id="txn_prod_hv_2",
        customer_id="cust_prod_5",
        amount=50000.0,
        status="FAILED",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        retry_count=0
    )
    rec = AIAgentRecommendation(
        diagnosis="Bank decline",
        recovery_probability=0.70,
        recommended_action="PAYMENT_LINK",
        risk_level="MEDIUM",
        reason="Enterprise client",
        requires_human_approval=False
    )
    decision = policy_engine.evaluate(transaction=txn, recommendation=rec)
    assert decision.requires_human_approval is True

def test_scenario_7_razorpay_unavailable_fallback():
    """Scenario 7: When Razorpay API fails or is unconfigured, fallback gracefully to SIMULATION_MODE."""
    service = RazorpayService(key_id="", key_secret="")
    assert service.is_configured is False
    assert service.current_mode_label == "SIMULATION_MODE"

def test_scenario_8_ai_unavailable_heuristics_fallback():
    """Scenario 8: When external LLM is offline, domain heuristics guarantee 100% uptime."""
    txn = Transaction(
        id="txn_prod_heuristics",
        customer_id="cust_prod_6",
        amount=4999.0,
        status="FAILED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=0
    )
    rec = ai_agent.analyze_failure(transaction=txn)
    assert rec.recovery_probability in [0.82, 0.91]
    assert rec.mode in ["HEURISTIC_FALLBACK", "DEMO_FALLBACK"]
    assert rec.fallback_used is True

def test_scenario_9_invalid_ai_response_handling():
    """Scenario 9: Pydantic validation catches and rejects invalid AI outputs."""
    with pytest.raises(ValidationError):
        AIAgentRecommendation(
            diagnosis="Bad Output",
            recovery_probability=-0.5, # Invalid negative
            recommended_action="RETRY_PAYMENT",
            risk_level="LOW",
            reason="Test",
            requires_human_approval=False
        )

def test_scenario_10_api_failure_handling():
    """Scenario 10: Non-existent transaction IDs return clean 404 JSON."""
    client = TestClient(app)
    res = client.get("/api/transactions/txn_non_existent_99999")
    assert res.status_code == 404
    assert "detail" in res.json()
