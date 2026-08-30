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
