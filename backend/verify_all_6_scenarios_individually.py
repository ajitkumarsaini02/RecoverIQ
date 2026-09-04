import json
import os
import sys
import time
from fastapi.testclient import TestClient
from app.main import app

def run_all_6_scenarios_individually():
    client = TestClient(app)

    scenarios = [
        "temporary_upi_failure",
        "bank_decline",
        "network_failure",
        "insufficient_funds",
        "repeated_failure",
        "high_value"
    ]

    results = []

    print("================================================================================")
    print("STARTING INDIVIDUAL EXECUTION & VERIFICATION OF ALL 6 SCENARIOS")
    print("================================================================================\n")

    for idx, sc_id in enumerate(scenarios, 1):
        print(f"\n>>> [{idx}/6] EXECUTING SCENARIO: {sc_id}")
        
        # Adding a short delay before calling Gemini to respect API quota window
        if idx > 1:
            time.sleep(3)

        response = client.post("/api/demo/scenario", json={"scenario": sc_id})
        assert response.status_code == 200, f"Scenario {sc_id} returned HTTP {response.status_code}: {response.text}"
        
        data = response.json()
        txn = data.get("transaction", {})
        ai = data.get("ai_analysis", {})
        pol = data.get("policy_decision", {})
        rec = data.get("recovery_result", {})
        audit = data.get("audit_timeline", [])

        # 1. Verify Gemini Result
        ai_mode = ai.get("mode")
        model_used = ai.get("model_used")
        fallback_used = ai.get("fallback_used")
        fallback_reason = ai.get("fallback_reason")

        assert ai_mode == "LIVE_LLM", f"[{sc_id}] Expected mode LIVE_LLM, got {ai_mode}"
        assert model_used == "gemini-3.8-flash", f"[{sc_id}] Expected model gemini-3.8-flash, got {model_used}"
        assert fallback_used is False, f"[{sc_id}] Expected fallback_used False, got {fallback_used}"
        assert fallback_reason is None, f"[{sc_id}] Expected fallback_reason None, got {fallback_reason}"

        # 2. Verify Retry Count Consistency
        txn_retry = txn.get("retry_count")
        pol_retry_consistent = True
        for r in pol.get("rules_evaluated", []):
            if r.get("rule_id") == "RULE_MAX_RETRIES":
                reason = r.get("reason", "")
                if f"({txn_retry})" not in reason and f"{txn_retry} attempted" not in reason:
                    pol_retry_consistent = False
                    print(f"[{sc_id}] Retry count mismatch in rule: txn={txn_retry}, reason={reason}")

        # Check policy reasons
        for r_reason in pol.get("reasons", []):
            if "Current retries (" in r_reason and f"({txn_retry})" not in r_reason:
                pol_retry_consistent = False
                print(f"[{sc_id}] Retry count mismatch in policy reasons: txn={txn_retry}, reason={r_reason}")

        # 3. Verify Recovery Semantics
        rec_status = rec.get("status")
        rec_amount = rec.get("recovered_amount")
        rzp_payment_id = txn.get("razorpay_payment_id")

        if sc_id == "repeated_failure":
            # Scenario 5: No automatic recovery execution if STOP_RECOVERY is selected
            assert pol.get("action") == "STOP" or not pol.get("allowed"), f"[{sc_id}] Expected STOP action"
            assert rec_status == "STOPPED", f"[{sc_id}] Expected STOPPED recovery status, got {rec_status}"
            assert txn.get("status") == "STOPPED", f"[{sc_id}] Expected STOPPED txn status"
        elif sc_id == "high_value":
            # Scenario 6: No automatic recovery execution before human approval
            assert pol.get("requires_human_approval") is True, f"[{sc_id}] Expected requires_human_approval=True"
            assert rec_status == "PENDING_APPROVAL", f"[{sc_id}] Expected PENDING_APPROVAL recovery status, got {rec_status}"
            assert txn.get("status") == "APPROVAL_REQUIRED", f"[{sc_id}] Expected APPROVAL_REQUIRED txn status"
        else:
            # Scenarios 1-4: Test Order creation alone must NEVER mark a transaction RECOVERED
            assert rec_status == "PENDING", f"[{sc_id}] Expected PENDING recovery status, got {rec_status}"
            assert rec_amount == 0.0, f"[{sc_id}] Expected recovered_amount 0.0, got {rec_amount}"
            assert rzp_payment_id is None, f"[{sc_id}] Expected razorpay_payment_id None, got {rzp_payment_id}"

        # Target ID (order id or payment link)
        rzp_order_id = rec.get("razorpay_order_id") or txn.get("razorpay_order_id")
        rzp_link = rec.get("razorpay_payment_link") or txn.get("razorpay_payment_link")
        order_or_link = rzp_order_id or rzp_link or "N/A"

        audit_summary = f"{len(audit)} events (" + ", ".join(e.get("event_type", "") for e in audit[:3]) + "...)"

        row = {
            "scenario_id": data.get("scenario_id"),
            "ai_mode": ai_mode,
            "model_used": model_used,
            "fallback_used": fallback_used,
            "recommended_action": ai.get("recommended_action"),
            "policy_allowed": pol.get("allowed"),
            "requires_human_approval": pol.get("requires_human_approval"),
            "recovery_action": rec.get("action_type"),
            "recovery_status": rec_status,
            "recovered_amount": rec_amount,
            "razorpay_order_id_or_payment_link": order_or_link,
            "audit_events": f"{len(audit)} events",
            "retry_count_consistency": f"Consistent ({txn_retry})" if pol_retry_consistent else f"Mismatch ({txn_retry})"
        }
        results.append(row)
        print(f"SUCCESS: {sc_id} verified.")
        print(f"  AI: {ai_mode} | {model_used} | fallback={fallback_used}")
        print(f"  Policy: allowed={pol.get('allowed')} | requires_approval={pol.get('requires_human_approval')}")
        print(f"  Recovery: action={rec.get('action_type')} | status={rec_status} | recovered=INR {rec_amount}")
        print(f"  Identifier: {order_or_link}")
        print(f"  Retries: consistent={pol_retry_consistent} (txn.retry_count={txn_retry})")

    print("\n================================================================================")
    print("ALL 6 SCENARIOS INDIVIDUALLY VERIFIED SUCCESSFULLY!")
    print("================================================================================\n")
    
    with open("scenario_verification_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(json.dumps(results, indent=2))
    return results

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    run_all_6_scenarios_individually()
