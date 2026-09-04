import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import Transaction, Customer, RecoveryAction, AuditEvent
from tests.conftest import TestSession

def test_complete_human_approval_workflow():
    """
    Test complete Human-in-the-Loop workflow:
    1. High-value failed payment detected (₹49,999)
    2. Policy engine gates action -> APPROVAL_REQUESTED
    3. Merchant reviews approval queue
    4. Merchant clicks APPROVE -> Action executed -> Revenue recovered -> APPROVED audit logged.
    """
    db = TestSession()
    cust = Customer(
        id="cust_appr_1",
        name="Dr. Sameer Saxena",
        email="sameer@medical.in",
        phone="+919876543210",
        lifetime_value=150000.0,
        successful_payments_count=5,
        failed_payments_count=1,
        risk_score=0.1
    )
    txn = Transaction(
        id="txn_appr_high_val",
        customer_id=cust.id,
        amount=49999.0,
        currency="INR",
        status="FAILED",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        customer_lifetime_value=150000.0,
        previous_successful_payments=5,
        previous_failed_payments=1,
        retry_count=0
    )
    db.add(cust)
    db.add(txn)
    db.commit()
    db.close()

    client = TestClient(app)

    # 1. Execute recovery (Should be gated for approval because amount >= ₹20,000)
    exec_res = client.post("/api/recovery/execute/txn_appr_high_val?mode=SIMULATION_MODE")
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["status"] == "REQUIRES_APPROVAL"
    assert exec_data["amount_recovered"] == 0.0

    # 2. Query Approval Queue
    appr_res = client.get("/api/approvals")
    assert appr_res.status_code == 200
    approvals = appr_res.json()
    assert len(approvals) >= 1

    target = next((a for a in approvals if a["transaction_id"] == "txn_appr_high_val"), None)
    assert target is not None
    assert target["transaction"]["amount"] == 49999.0
    assert target["transaction"]["failure_reason"] == "BANK_DECLINED"
    assert "ai_diagnosis" in target
    assert "ai_probability" in target
    assert "ai_risk_level" in target
    assert "ai_reasoning" in target
    assert "policy_decision" in target
    action_id = target["id"]

    # 3. Approve Action
    approve_res = client.post(f"/api/recovery/approve/{action_id}")
    assert approve_res.status_code == 200
    approve_data = approve_res.json()
    assert approve_data["status"] == "APPROVED_AND_EXECUTED"
    assert approve_data["recovered_amount"] == 49999.0

    # 4. Verify transaction status in DB is now RECOVERED
    detail_res = client.get("/api/transactions/txn_appr_high_val")
    assert detail_res.status_code == 200
    assert detail_res.json()["status"] == "RECOVERED"

    # 5. Verify APPROVED Audit Event
    audit_res = client.get("/api/audit?transaction_id=txn_appr_high_val")
    assert audit_res.status_code == 200
    events = audit_res.json()
    event_types = [e["event_type"] for e in events]
    assert "APPROVED" in event_types or "HUMAN_APPROVED" in event_types

def test_human_rejection_workflow():
    """
    Test merchant rejection workflow:
    1. High-value transaction gated
    2. Merchant clicks REJECT -> Action rejected -> Transaction STOPPED -> REJECTED audit logged.
    """
    db = TestSession()
    cust = Customer(
        id="cust_appr_2",
        name="Vikram Seth",
        email="vikram@corp.in",
        phone="+919876543219",
        lifetime_value=50000.0,
        successful_payments_count=2,
        failed_payments_count=2,
        risk_score=0.3
    )
    txn = Transaction(
        id="txn_appr_reject_val",
        customer_id=cust.id,
        amount=25000.0,
        currency="INR",
        status="FAILED",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        customer_lifetime_value=50000.0,
        previous_successful_payments=2,
        previous_failed_payments=2,
        retry_count=0
    )
    db.add(cust)
    db.add(txn)
    db.commit()
    db.close()

    client = TestClient(app)

    # 1. Trigger recovery execution (gates for approval)
    client.post("/api/recovery/execute/txn_appr_reject_val")

    # 2. Query Approval Queue
    appr_res = client.get("/api/approvals")
    assert appr_res.status_code == 200
    approvals = appr_res.json()
    target = next((a for a in approvals if a["transaction_id"] == "txn_appr_reject_val"), None)
    assert target is not None
    action_id = target["id"]

    # 3. Reject Action
    reject_res = client.post(f"/api/recovery/reject/{action_id}", json={"reason": "Customer flagged by risk ops"})
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "REJECTED"

    # 4. Verify transaction status in DB is now STOPPED
    detail_res = client.get("/api/transactions/txn_appr_reject_val")
    assert detail_res.status_code == 200
    assert detail_res.json()["status"] == "STOPPED"

    # 5. Verify REJECTED Audit Event
    audit_res = client.get("/api/audit?transaction_id=txn_appr_reject_val")
    assert audit_res.status_code == 200
    events = audit_res.json()
    event_types = [e["event_type"] for e in events]
    assert "REJECTED" in event_types or "HUMAN_REJECTED" in event_types

def test_duplicate_approve_and_state_guards():
    """Verify that approving/rejecting already finalized actions is safely handled and invalid IDs return 404."""
    client = TestClient(app)
    db = TestSession()
    cust = Customer(
        id="cust_appr_guard_1",
        name="State Guard Customer",
        email="guard@domain.in",
        phone="+919811223377",
        lifetime_value=60000.0,
        successful_payments_count=3,
        failed_payments_count=0,
        risk_score=0.1
    )
    txn = Transaction(
        id="txn_appr_guard_1",
        customer_id=cust.id,
        amount=30000.0, # High value
        currency="INR",
        status="FAILED",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        retry_count=0
    )
    db.add(cust)
    db.add(txn)
    db.commit()

    # Trigger recovery execution -> Gates for approval
    client.post("/api/recovery/execute/txn_appr_guard_1")

    # Get action ID
    appr_res = client.get("/api/approvals")
    target = next(a for a in appr_res.json() if a["transaction_id"] == "txn_appr_guard_1")
    act_id = target["id"]

    # 1. Approve once
    res1 = client.post(f"/api/recovery/approve/{act_id}")
    assert res1.status_code == 200

    # 2. Duplicate Approve -> Safely rejected with HTTP 400
    res2 = client.post(f"/api/recovery/approve/{act_id}")
    assert res2.status_code == 400
    assert "cannot be approved" in res2.json()["detail"].lower()

    # 3. Reject after Approve -> Safely rejected with HTTP 400
    res3 = client.post(f"/api/recovery/reject/{act_id}", json={"reason": "Late rejection attempt"})
    assert res3.status_code == 400
    assert "cannot be rejected" in res3.json()["detail"].lower()

    # 4. Invalid Action ID -> 404
    res4 = client.post("/api/recovery/approve/act_non_existent_999")
    assert res4.status_code == 404

    res5 = client.post("/api/recovery/reject/act_non_existent_999")
    assert res5.status_code == 404
    db.close()
