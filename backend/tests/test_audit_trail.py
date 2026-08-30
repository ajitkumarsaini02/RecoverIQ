import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.audit_service import audit_service
from tests.conftest import TestSession

def test_audit_service_and_event_types():
    """Test recording all 12 core financial audit event types."""
    db = TestSession()
    txn_id = "txn_audit_test_99"

    # 1. PAYMENT_FAILED
    e1 = audit_service.log_payment_failed(db=db, transaction_id=txn_id, amount=4999.0, failure_reason="UPI_TIMEOUT")
    assert e1.event_type == "PAYMENT_FAILED"
    assert e1.actor == "RAZORPAY_GATEWAY"

    # 2. FAILURE_ANALYZED
    e2 = audit_service.log_failure_analyzed(db=db, transaction_id=txn_id, diagnosis="Transient UPI timeout", failure_reason="UPI_TIMEOUT")
    assert e2.event_type == "FAILURE_ANALYZED"
    assert e2.actor == "AI_AGENT"

    # 3. CUSTOMER_CONTEXT_ANALYZED
    e3 = audit_service.log_customer_context_analyzed(db=db, transaction_id=txn_id, customer_id="cust_1", customer_ltv=39992.0, successful_payments=8, failed_payments=1)
    assert e3.event_type == "CUSTOMER_CONTEXT_ANALYZED"

    # 4. AI_RECOMMENDATION
    e4 = audit_service.log_ai_recommendation(db=db, transaction_id=txn_id, action="RETRY_PAYMENT", probability=0.91, risk_level="LOW", reason="Strong track record")
    assert e4.event_type == "AI_RECOMMENDATION"

    # 5. POLICY_VALIDATED
    e5 = audit_service.log_policy_validated(db=db, transaction_id=txn_id, allowed=True, action="RETRY_PAYMENT", requires_human_approval=False, reason="Within limits")
    assert e5.event_type == "POLICY_VALIDATED"

    # 6. APPROVAL_REQUESTED
    e6 = audit_service.log_approval_requested(db=db, transaction_id=txn_id, action_id="act_1", amount=49999.0, reason="High value")
    assert e6.event_type == "APPROVAL_REQUESTED"

    # 7. ACTION_APPROVED
    e7 = audit_service.log_action_approved(db=db, transaction_id=txn_id, action_id="act_1")
    assert e7.event_type == "ACTION_APPROVED"

    # 8. ACTION_REJECTED
    e8 = audit_service.log_action_rejected(db=db, transaction_id=txn_id, action_id="act_2", reason="Risk ops rejected")
    assert e8.event_type == "ACTION_REJECTED"

    # 9. RECOVERY_EXECUTED
    e9 = audit_service.log_recovery_executed(db=db, transaction_id=txn_id, action="RETRY_PAYMENT", mode="TEST_MODE")
    assert e9.event_type == "RECOVERY_EXECUTED"

    # 10. RECOVERY_SUCCEEDED
    e10 = audit_service.log_recovery_succeeded(db=db, transaction_id=txn_id, amount_recovered=4999.0, mode="TEST_MODE")
    assert e10.event_type == "RECOVERY_SUCCEEDED"

    # 11. RECOVERY_FAILED
    e11 = audit_service.log_recovery_failed(db=db, transaction_id=txn_id, error_message="Issuer timeout")
    assert e11.event_type == "RECOVERY_FAILED"

    # 12. RECOVERY_STOPPED
    e12 = audit_service.log_recovery_stopped(db=db, transaction_id=txn_id, reason="Max retries reached")
    assert e12.event_type == "RECOVERY_STOPPED"

    db.close()

def test_api_get_audit_trail_filtering():
    """Test GET /api/audit filtering by transaction_id and actor."""
    client = TestClient(app)

    # Fetch audit events for specific transaction
    res = client.get("/api/audit?transaction_id=txn_audit_test_99")
    assert res.status_code == 200
    events = res.json()
    assert len(events) >= 10
    for e in events:
        assert e["transaction_id"] == "txn_audit_test_99"

    # Fetch audit events filtered by actor
    res_ai = client.get("/api/audit?actor=AI_AGENT")
    assert res_ai.status_code == 200
    ai_events = res_ai.json()
    assert len(ai_events) > 0
    for e in ai_events:
        assert e["actor"] == "AI_AGENT"

def test_audit_trail_success_recovery_consistency():
    """Verify that a successful recovery pipeline creates consistent audit events without contradictions."""
    client = TestClient(app)
    res = client.post("/api/demo/scenario", json={"scenario": "temporary_upi_failure", "mode": "SIMULATION_MODE"})
    assert res.status_code == 200
    data = res.json()

    txn = data["transaction"]
    recov = data["recovery_result"]
    events = data["audit_timeline"]

    # Assert no contradictions across state layers
    assert txn["status"] == "RECOVERED"
    assert recov["status"] == "SUCCESS"
    assert recov["recovered_amount"] == txn["amount"]
    assert txn["razorpay_payment_id"] is not None

    event_types = [e["event_type"] for e in events]
    assert "PAYMENT_FAILED_DETECTED" in event_types or "PAYMENT_FAILED" in event_types
    assert "AI_ANALYSIS_COMPLETED" in event_types or "FAILURE_ANALYZED" in event_types
    assert "POLICY_EVALUATED" in event_types or "POLICY_VALIDATED" in event_types
    assert "PAYMENT_RECOVERED" in event_types

    # Ensure no secrets leak into audit details
    for e in events:
        details_str = str(e.get("details", {})).lower()
        assert "key_secret" not in details_str
        assert "api_key" not in details_str

def test_audit_trail_stopped_recovery_consistency():
    """Verify that a max-retries stopped transaction generates correct stop audit trail."""
    client = TestClient(app)
    res = client.post("/api/demo/scenario", json={"scenario": "repeated_failure", "mode": "SIMULATION_MODE"})
    assert res.status_code == 200
    data = res.json()

    txn = data["transaction"]
    recov = data["recovery_result"]
    events = data["audit_timeline"]

    assert txn["status"] == "STOPPED"
    assert recov["status"] == "STOPPED"
    assert recov["recovered_amount"] == 0.0

    event_types = [e["event_type"] for e in events]
    assert "RECOVERY_STOPPED" in event_types
    # Must NOT have PAYMENT_RECOVERED or RECOVERY_EXECUTED
    assert "PAYMENT_RECOVERED" not in event_types
