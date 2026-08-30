import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_playground_all_6_scenarios_e2e():
    client = TestClient(app)

    # Scenario 1: Temporary UPI Failure (Flagship Demo)
    res1 = client.post("/api/demo/scenario", json={"scenario_id": "temporary_upi_failure"})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["scenario_id"] == "temporary_upi_failure"
    assert data1["transaction"]["amount"] == 4999.0
    assert data1["transaction"]["failure_reason"] == "UPI_TIMEOUT"
    assert data1["ai_analysis"]["recommended_action"] == "RETRY_PAYMENT"
    assert data1["ai_analysis"]["recovery_probability"] >= 0.85
    assert data1["policy_decision"]["allowed"] is True
    assert data1["recovery_result"]["status"] == "SUCCESS"
    assert data1["recovery_result"]["recovered_amount"] == 4999.0
    assert len(data1["audit_timeline"]) >= 4

    # Scenario 2: Bank Decline
    res2 = client.post("/api/demo/scenario", json={"scenario_id": "bank_decline"})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["scenario_id"] == "bank_decline"
    assert data2["transaction"]["amount"] == 2499.0
    assert data2["ai_analysis"]["recommended_action"] in ["ALTERNATIVE_PAYMENT_METHOD", "PAYMENT_LINK"]

    # Scenario 3: Network Failure
    res3 = client.post("/api/demo/scenario", json={"scenario_id": "network_failure"})
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["scenario_id"] == "network_failure"
    assert data3["transaction"]["amount"] == 999.0
    assert data3["recovery_result"]["recovered_amount"] == 999.0

    # Scenario 4: Insufficient Funds
    res4 = client.post("/api/demo/scenario", json={"scenario_id": "insufficient_funds"})
    assert res4.status_code == 200
    data4 = res4.json()
    assert data4["scenario_id"] == "insufficient_funds"
    assert data4["transaction"]["amount"] == 14999.0
    assert data4["ai_analysis"]["recommended_action"] == "PAYMENT_LINK"

    # Scenario 5: Repeated Failure (Cap Reached -> STOP)
    res5 = client.post("/api/demo/scenario", json={"scenario_id": "repeated_failure"})
    assert res5.status_code == 200
    data5 = res5.json()
    assert data5["scenario_id"] == "repeated_failure"
    assert data5["policy_decision"]["allowed"] is False
    assert data5["recovery_result"]["status"] in ["STOPPED", "REJECTED"]
    assert data5["recovery_result"]["recovered_amount"] == 0.0

    # Scenario 6: High-Value Enterprise Payment (Gated for Human Approval)
    res6 = client.post("/api/demo/scenario", json={"scenario_id": "high_value_transaction"})
    assert res6.status_code == 200
    data6 = res6.json()
    assert data6["scenario_id"] == "high_value_transaction"
    assert data6["transaction"]["amount"] == 49999.0
    assert data6["policy_decision"]["requires_human_approval"] is True
    assert data6["recovery_result"]["status"] == "PENDING_APPROVAL"
    assert data6["recovery_result"]["recovered_amount"] == 0.0
