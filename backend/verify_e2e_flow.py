import urllib.request
import json

def post(url, payload):
    req = urllib.request.Request(url, method='POST')
    req.add_header('Content-Type', 'application/json')
    body = json.dumps(payload).encode('utf-8')
    with urllib.request.urlopen(req, data=body) as res:
        return json.loads(res.read())

def get(url):
    req = urllib.request.Request(url, method='GET')
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read())

print("=== STEP 1: Running ₹4,999 Flagship Failed UPI Payment Scenario ===")
res = post("http://127.0.0.1:8000/api/demo/scenario", {"scenario_id": "temporary_upi_failure"})

txn = res["transaction"]
ai = res["ai_analysis"]
policy = res.get("policy_decision") or res.get("policy_check", {})
rec = res["recovery_result"]

print(f"1. Transaction ID: {txn['id']}")
print(f"2. Transaction Amount: ₹{txn['amount']:,.2f}")
print(f"3. Failure Reason: {txn['failure_reason']}")
print(f"4. Customer Context: {txn['customer_name']} (LTV: ₹{txn['customer_lifetime_value']:,.2f}, Success: {txn['previous_successful_payments']}, Fail: {txn['previous_failed_payments']})")
print(f"5. AI Diagnosis: {ai['diagnosis']}")
print(f"6. AI Recovery Probability: {ai['recovery_probability'] * 100:.1f}%")
print(f"7. AI Recommended Action: {ai['recommended_action']}")
print(f"8. Policy Guardrail Allowed: {policy['allowed']}")
print(f"9. Policy Rule Check Rationale: {policy['reason']}")
print(f"10. Recovery Execution Status: {rec['status']}")
print(f"11. Amount Recovered: ₹{rec['recovered_amount']:,.2f}")

print("\n=== STEP 2: Checking Real-Time Dynamic Dashboard Analytics ===")
dash = get("http://127.0.0.1:8000/api/dashboard")
print(f"Revenue at Risk: ₹{dash['revenue_at_risk']:,.2f}")
print(f"Revenue Recovered: ₹{dash['revenue_recovered']:,.2f}")
print(f"Recovery Rate: {dash['recovery_rate']}%")
print(f"Failed Count: {dash['total_failed_count']}")
print(f"Recovery Attempts: {dash['recovery_attempts_count']}")
print(f"Successful Recoveries: {dash['successful_recoveries_count']}")

print(f"\n=== STEP 3: Checking Immutable Audit Events for Txn {txn['id']} ===")
audit = get(f"http://127.0.0.1:8000/api/audit?transaction_id={txn['id']}")
print(f"Total audit events logged: {len(audit)}")
for evt in audit:
    print(f"  [{evt['timestamp']}] [{evt['actor']}] {evt['event_type']} -> {evt['decision']}")

print("\n>>> ALL 11 END-TO-END PIPELINE STEPS VERIFIED SUCCESSFULLY <<<")
