import json
import os
import sys
from fastapi.testclient import TestClient
from app.main import app

def test_all_6_scenarios():
    client = TestClient(app)

    scenarios = [
        "temporary_upi_failure",
        "bank_decline",
        "network_failure",
        "insufficient_funds",
        "repeated_failure",
        "high_value" # Using the exact alias requested by user
    ]

    results = []

    for sc_id in scenarios:
        print(f"\n==================== TRIGGERING SCENARIO: {sc_id} ====================")
        response = client.post("/api/demo/scenario", json={"scenario": sc_id})
        assert response.status_code == 200, f"Scenario {sc_id} failed with {response.status_code}: {response.text}"
        data = response.json()

        txn = data.get("transaction", {})
        ai = data.get("ai_analysis", {})
        pol = data.get("policy_decision", {})
        rec = data.get("recovery_result", {})
        audit = data.get("audit_timeline", [])

        # Verify retry count consistency
        txn_retry = txn.get("retry_count")
        pol_retry_consistent = True
        for r in pol.get("rules_evaluated", []):
            if r.get("rule_id") == "RULE_MAX_RETRIES":
                reason = r.get("reason", "")
                if f"({txn_retry})" not in reason:
                    pol_retry_consistent = False
                    print(f"WARNING: retry_count mismatch in rule! txn={txn_retry}, rule={reason}")

        # Summary entry for table
        row = {
            "scenario_id": data.get("scenario_id"),
            "input_scenario": sc_id,
            "ai_mode": ai.get("mode"),
            "model_used": ai.get("model_used"),
            "fallback_used": ai.get("fallback_used"),
            "recommended_action": ai.get("recommended_action"),
            "policy_allowed": pol.get("allowed"),
            "requires_human_approval": pol.get("requires_human_approval"),
            "recovery_action": rec.get("action_type"),
            "recovery_status": rec.get("status"),
            "recovered_amount": rec.get("recovered_amount"),
            "razorpay_order_id": rec.get("razorpay_order_id") or txn.get("razorpay_order_id"),
            "payment_link": rec.get("razorpay_payment_link") or txn.get("razorpay_payment_link"),
            "audit_events_count": len(audit),
            "audit_event_types": [e.get("event_type") for e in audit],
            "retry_count": txn_retry,
            "retry_count_consistent": pol_retry_consistent,
            "transaction_status": txn.get("status")
        }
        results.append(row)
        print(json.dumps(row, indent=2))

    print("\n\n==================== FINAL COMPILATION TABLE ====================")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    test_all_6_scenarios()
