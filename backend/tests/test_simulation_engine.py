import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import Transaction, RecoveryAction, AuditEvent
from tests.conftest import TestSession

def test_simulation_full_lifecycle():
    """
    Test the complete 11-step portfolio simulation execution:
    1. Loads failed transactions
    2. Calculates initial revenue at risk
    3. Runs AI diagnosis
    4. Evaluates policy engine rules
    5. Executes allowed actions safely
    6. Generates realistic outcomes
    7. Calculates recovered revenue dynamically
    8. Calculates recovery rate
    9. Saves results & updates DB
    10. Updates dashboard metrics
    11. Generates audit events.
    """
    client = TestClient(app)

    # 1. Trigger batch simulation
    res = client.post("/api/simulation/run?limit=100")
    assert res.status_code == 200
    data = res.json()

    # 2. Verify all dynamic calculation outputs
    assert "simulation_id" in data
    assert data["transactions_evaluated"] > 0
    assert data["initial_revenue_at_risk"] > 0.0
    assert data["recovery_attempts"] >= 0
    assert data["successful_recoveries"] >= 0
    assert data["revenue_recovered"] >= 0.0
    assert 0.0 <= data["recovery_rate"] <= 100.0
    assert data["stopped_cases"] >= 0
    assert data["pending_approvals_generated"] >= 0
    assert data["data_label"] == "Synthetic/Test Data — Not Live Merchant Revenue"

    # 3. Verify that DB records were updated
    db = TestSession()
    recovered_count = db.query(Transaction).filter(Transaction.status == "RECOVERED").count()
    assert recovered_count > 0

    actions_count = db.query(RecoveryAction).count()
    assert actions_count > 0

    # 4. Verify audit events were recorded
    audit_events_count = db.query(AuditEvent).count()
    assert audit_events_count > 0
    db.close()

    # 5. Verify that GET /api/dashboard reflects the simulation results
    dash_res = client.get("/api/dashboard")
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["revenue_recovered"] >= data["revenue_recovered"]
    assert dash_data["successful_recoveries_count"] >= data["successful_recoveries"]
