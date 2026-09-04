import logging
import uuid
import json
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

from app.db.session import get_db
from app.db.models import Customer, Transaction, RecoveryAction, AuditEvent
from app.services.razorpay_service import razorpay_service
from app.services.ai_agent import ai_agent, AIAgentRecommendation
from app.services.policy_engine import policy_engine, PolicyEvaluationResult

router = APIRouter(prefix="/api/demo", tags=["Demo & Scenarios"])

class DemoPaymentRequest(BaseModel):
    amount: float = Field(default=4999.0, ge=1.0)
    customer_name: str = Field(default="Priya Sharma")
    customer_email: str = Field(default="priya.sharma@gmail.com")
    customer_phone: str = Field(default="+919876543210")
    payment_method: str = Field(default="UPI")
    simulate_failure: bool = Field(default=True)
    failure_reason: str = Field(default="UPI_TIMEOUT")

class DemoScenarioRequest(BaseModel):
    scenario: Optional[str] = Field(default=None, description="Scenario ID")
    scenario_id: Optional[str] = Field(default=None, description="Scenario ID alias")
    mode: Optional[str] = Field(default=None, description="Execution Mode: TEST_MODE or SIMULATION_MODE")

PRESET_SCENARIOS = {
    "temporary_upi_failure": {
        "title": "Scenario 1: Temporary UPI Failure (₹4,999)",
        "amount": 4999.0,
        "payment_method": "UPI",
        "failure_reason": "UPI_TIMEOUT",
        "error_code": "PSP_TIMEOUT",
        "customer": {
            "name": "Priya Sharma",
            "email": "priya.sharma@gmail.com",
            "phone": "+91 98201 44521",
            "lifetime_value": 39992.0,
            "successful_payments_count": 8,
            "failed_payments_count": 1,
            "risk_score": 0.08
        },
        "retries_so_far": 0,
        "simulate_recovery_success": True
    },
    "bank_decline": {
        "title": "Scenario 2: Bank Issuer Decline (₹2,499)",
        "amount": 2499.0,
        "payment_method": "CARD",
        "failure_reason": "BANK_DECLINED",
        "error_code": "ISSUER_DECLINE",
        "customer": {
            "name": "Rahul Verma",
            "email": "rahul.verma@corp.in",
            "phone": "+91 98451 90123",
            "lifetime_value": 14994.0,
            "successful_payments_count": 6,
            "failed_payments_count": 2,
            "risk_score": 0.22
        },
        "retries_so_far": 0,
        "simulate_recovery_success": True
    },
    "network_failure": {
        "title": "Scenario 3: Network Drop & Gateway Latency (₹999)",
        "amount": 999.0,
        "payment_method": "UPI",
        "failure_reason": "NETWORK_ERROR",
        "error_code": "GATEWAY_TIMEOUT",
        "customer": {
            "name": "Ananya Patel",
            "email": "ananya.patel@gmail.com",
            "phone": "+91 97123 45678",
            "lifetime_value": 9990.0,
            "successful_payments_count": 10,
            "failed_payments_count": 0,
            "risk_score": 0.04
        },
        "retries_so_far": 0,
        "simulate_recovery_success": True
    },
    "insufficient_funds": {
        "title": "Scenario 4: Insufficient Account Balance (₹14,999)",
        "amount": 14999.0,
        "payment_method": "NETBANKING",
        "failure_reason": "INSUFFICIENT_FUNDS",
        "error_code": "INSUFFICIENT_BALANCE",
        "customer": {
            "name": "Rohan Gupta",
            "email": "rohan.gupta@enterprise.co",
            "phone": "+91 99887 76655",
            "lifetime_value": 29998.0,
            "successful_payments_count": 2,
            "failed_payments_count": 2,
            "risk_score": 0.35
        },
        "retries_so_far": 0,
        "simulate_recovery_success": True
    },
    "repeated_failure": {
        "title": "Scenario 5: Repeated Failure Cap Reached (₹4,999)",
        "amount": 4999.0,
        "payment_method": "CARD",
        "failure_reason": "BANK_DECLINED",
        "error_code": "CARD_RESTRICTED",
        "customer": {
            "name": "Vikram Singh",
            "email": "vikram.singh@yahoo.in",
            "phone": "+91 98111 22334",
            "lifetime_value": 4999.0,
            "successful_payments_count": 1,
            "failed_payments_count": 3,
            "risk_score": 0.65
        },
        "retries_so_far": 2,
        "simulate_recovery_success": False
    },
    "high_value_transaction": {
        "title": "Scenario 6: High-Value Enterprise Payment (₹49,999)",
        "amount": 49999.0,
        "payment_method": "CARD",
        "failure_reason": "BANK_DECLINED",
        "error_code": "HIGH_VALUE_SECURITY_HOLD",
        "customer": {
            "name": "Dr. Sameer Saxena",
            "email": "sameer.saxena@medical.in",
            "phone": "+91 98777 88990",
            "lifetime_value": 149997.0,
            "successful_payments_count": 3,
            "failed_payments_count": 1,
            "risk_score": 0.15
        },
        "retries_so_far": 0,
        "simulate_recovery_success": True
    }
}

@router.post("/scenario")
async def run_scenario(request: DemoScenarioRequest, db: Session = Depends(get_db)):
    """
    Executes the flagship 7-step revenue recovery pipeline:
    Payment Attempt -> Failure -> AI Diagnosis -> Policy Engine Guardrails -> Safe Execution -> Verification & Audit.
    Supports explicit TEST_MODE (real Razorpay + Gemini) and SIMULATION_MODE.
    """
    raw_key = request.scenario or request.scenario_id or ""
    scenario_key = raw_key.lower().replace(" ", "_").strip()
    if scenario_key in ["high_value", "high_value_payment", "high_value_order"]:
        scenario_key = "high_value_transaction"
    if scenario_key in ["repeated_failures", "repeated_failure_cap", "retry_limit"]:
        scenario_key = "repeated_failure"

    if scenario_key not in PRESET_SCENARIOS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown scenario '{raw_key}'. Available: {list(PRESET_SCENARIOS.keys())}"
        )

    spec = PRESET_SCENARIOS[scenario_key]
    cust_data = spec["customer"]
    now = datetime.now(timezone.utc)

    # Determine execution mode
    exec_mode = request.mode or ("TEST_MODE" if razorpay_service.is_live_test_mode else "SIMULATION_MODE")

    # 1. Create / Retrieve Customer
    cust_id = f"cust_demo_{uuid.uuid4().hex[:8]}"
    customer = Customer(
        id=cust_id,
        name=cust_data["name"],
        email=cust_data["email"],
        phone=cust_data["phone"],
        lifetime_value=cust_data["lifetime_value"],
        successful_payments_count=cust_data["successful_payments_count"],
        failed_payments_count=cust_data["failed_payments_count"],
        risk_score=cust_data["risk_score"],
        created_at=now,
        updated_at=now
    )
    db.add(customer)
    db.flush()

    # 2. Razorpay Order Creation (Test Mode or Simulation)
    order_result = await razorpay_service.create_order(
        amount_in_inr=spec["amount"],
        receipt=f"rcpt_demo_{uuid.uuid4().hex[:6]}",
        notes={"scenario": spec["title"]},
        force_mode=exec_mode
    )

    # 3. Create Failed Transaction in DB
    txn_id = f"txn_demo_{uuid.uuid4().hex[:8]}"
    txn = Transaction(
        id=txn_id,
        customer_id=customer.id,
        amount=spec["amount"],
        currency="INR",
        status="FAILED",
        payment_method=spec["payment_method"],
        failure_reason=spec["failure_reason"],
        error_code=spec["error_code"],
        customer_lifetime_value=customer.lifetime_value,
        previous_successful_payments=customer.successful_payments_count,
        previous_failed_payments=customer.failed_payments_count,
        previous_recovery_attempts=spec["retries_so_far"],
        retry_count=spec["retries_so_far"],
        max_retries=2,
        razorpay_order_id=order_result.get("id"),
        created_at=now,
        updated_at=now
    )
    db.add(txn)

    # Audit 1: Failure detected
    aud_fail = AuditEvent(
        id=f"aud_{uuid.uuid4().hex[:12]}",
        timestamp=now,
        transaction_id=txn.id,
        event_type="PAYMENT_FAILED_DETECTED",
        actor="RAZORPAY_GATEWAY",
        decision="FAILURE_RECORDED",
        details_json=json.dumps({
            "amount": spec["amount"],
            "failure_reason": spec["failure_reason"],
            "error_code": spec["error_code"],
            "razorpay_order_id": order_result.get("id"),
            "mode": exec_mode
        })
    )
    db.add(aud_fail)

    # 4. AI Agent Analysis (Structured Pydantic)
    ai_analysis = ai_agent.analyze_failure(transaction=txn, customer=customer)
    
    # Audit 2: AI Analysis Complete
    aud_ai = AuditEvent(
        id=f"aud_{uuid.uuid4().hex[:12]}",
        timestamp=now + timedelta(milliseconds=200),
        transaction_id=txn.id,
        event_type="AI_ANALYSIS_COMPLETED",
        actor="AI_AGENT",
        decision=ai_analysis.recommended_action,
        details_json=json.dumps({
            "diagnosis": ai_analysis.diagnosis,
            "recovery_probability": ai_analysis.recovery_probability,
            "risk_level": ai_analysis.risk_level,
            "reason": ai_analysis.reason,
            "requires_human_approval": ai_analysis.requires_human_approval,
            "model_used": ai_analysis.model_used,
            "fallback_used": ai_analysis.fallback_used
        })
    )
    db.add(aud_ai)

    # 5. Deterministic Policy Engine Validation
    policy_res = policy_engine.evaluate(transaction=txn, recommendation=ai_analysis)

    # Audit 3: Policy Evaluated
    aud_policy = AuditEvent(
        id=f"aud_{uuid.uuid4().hex[:12]}",
        timestamp=now + timedelta(milliseconds=400),
        transaction_id=txn.id,
        event_type="POLICY_EVALUATED",
        actor="POLICY_ENGINE",
        decision="APPROVED" if (policy_res.allowed and not policy_res.requires_human_approval) else ("HUMAN_APPROVAL_REQUIRED" if policy_res.requires_human_approval else "REJECTED_OR_STOPPED"),
        details_json=json.dumps({
            "action": policy_res.action,
            "allowed": policy_res.allowed,
            "requires_human_approval": policy_res.requires_human_approval,
            "reasons": policy_res.reasons,
            "rules_count": len(policy_res.rules_evaluated)
        })
    )
    db.add(aud_policy)

    # 6. Execute Recovery or Gate for Approval
    execution_result = {
        "execution_id": f"exec_{uuid.uuid4().hex[:10]}",
        "transaction_id": txn.id,
        "action_type": policy_res.action,
        "status": "PENDING",
        "recovered_amount": 0.0,
        "mode": exec_mode,
        "executed_at": (now + timedelta(milliseconds=700)).isoformat(),
        "message": ""
    }

    if policy_res.requires_human_approval:
        txn.status = "APPROVAL_REQUIRED"
        execution_result["status"] = "PENDING_APPROVAL"
        execution_result["message"] = "High-value or high-risk transaction gated. Pending merchant approval in Approval Queue."
        
        # Action record in pending status
        action_rec = RecoveryAction(
            id=f"act_{uuid.uuid4().hex[:12]}",
            transaction_id=txn.id,
            action_type=policy_res.action,
            status="PENDING_APPROVAL",
            ai_diagnosis=ai_analysis.diagnosis,
            ai_probability=ai_analysis.recovery_probability,
            ai_risk_level=ai_analysis.risk_level,
            ai_reasoning=ai_analysis.reason,
            policy_allowed=policy_res.allowed,
            policy_reasons_json=json.dumps(policy_res.reasons),
            requires_human_approval=True,
            recovered_amount=0.0,
            execution_details_json=json.dumps({"gated": True, "threshold": 20000.0}),
            mode=exec_mode,
            created_at=now + timedelta(milliseconds=500)
        )
        db.add(action_rec)

        aud_gate = AuditEvent(
            id=f"aud_{uuid.uuid4().hex[:12]}",
            timestamp=now + timedelta(milliseconds=600),
            transaction_id=txn.id,
            event_type="HUMAN_APPROVAL_REQUESTED",
            actor="POLICY_ENGINE",
            decision="GATED_FOR_APPROVAL",
            details_json=json.dumps({"action_id": action_rec.id, "amount": txn.amount})
        )
        db.add(aud_gate)

    elif policy_res.action == "STOP" or not policy_res.allowed:
        txn.status = "STOPPED"
        execution_result["status"] = "STOPPED"
        execution_result["message"] = "Recovery safely bounded and halted by Merchant Policy Engine."

        action_rec = RecoveryAction(
            id=f"act_{uuid.uuid4().hex[:12]}",
            transaction_id=txn.id,
            action_type="STOP",
            status="REJECTED",
            ai_diagnosis=ai_analysis.diagnosis,
            ai_probability=ai_analysis.recovery_probability,
            ai_risk_level=ai_analysis.risk_level,
            ai_reasoning=ai_analysis.reason,
            policy_allowed=False,
            policy_reasons_json=json.dumps(policy_res.reasons),
            requires_human_approval=False,
            recovered_amount=0.0,
            mode=exec_mode,
            created_at=now + timedelta(milliseconds=500),
            executed_at=now + timedelta(milliseconds=600)
        )
        db.add(action_rec)

        aud_stop = AuditEvent(
            id=f"aud_{uuid.uuid4().hex[:12]}",
            timestamp=now + timedelta(milliseconds=600),
            transaction_id=txn.id,
            event_type="RECOVERY_STOPPED",
            actor="POLICY_ENGINE",
            decision="STOP_ENFORCED",
            details_json=json.dumps({"reasons": policy_res.reasons})
        )
        db.add(aud_stop)

    else:
        # Policy Approved -> Execute Recovery
        if policy_res.action in ["RETRY_PAYMENT", "ALTERNATIVE_PAYMENT_METHOD"]:
            if exec_mode == "SIMULATION_MODE":
                txn.status = "RECOVERED"
                txn.retry_count += 1
                sim_pay_id = f"pay_sim_{uuid.uuid4().hex[:12]}"
                txn.razorpay_payment_id = sim_pay_id
                execution_result["status"] = "SUCCESS"
                execution_result["recovered_amount"] = txn.amount
                execution_result["message"] = f"[SIMULATED RECOVERY] Simulated recovery executed successfully. ₹{txn.amount:,.0f} recovered (Simulation Sandbox)."

                action_rec = RecoveryAction(
                    id=f"act_{uuid.uuid4().hex[:12]}",
                    transaction_id=txn.id,
                    action_type=policy_res.action,
                    status="SUCCESS",
                    ai_diagnosis=ai_analysis.diagnosis,
                    ai_probability=ai_analysis.recovery_probability,
                    ai_risk_level=ai_analysis.risk_level,
                    ai_reasoning=ai_analysis.reason,
                    policy_allowed=True,
                    policy_reasons_json=json.dumps(policy_res.reasons),
                    requires_human_approval=False,
                    recovered_amount=txn.amount,
                    execution_details_json=json.dumps({"payment_id": sim_pay_id, "status": "simulated_captured"}),
                    mode="SIMULATION_MODE",
                    created_at=now + timedelta(milliseconds=500),
                    executed_at=now + timedelta(milliseconds=700)
                )
                db.add(action_rec)

                aud_succ = AuditEvent(
                    id=f"aud_{uuid.uuid4().hex[:12]}",
                    timestamp=now + timedelta(milliseconds=700),
                    transaction_id=txn.id,
                    event_type="PAYMENT_RECOVERED",
                    actor="AI_AGENT",
                    decision="REVENUE_RECOVERED",
                    details_json=json.dumps({
                        "recovered_amount": txn.amount,
                        "mode": "SIMULATION_MODE",
                        "action": policy_res.action
                    })
                )
                db.add(aud_succ)

            else:
                # Real TEST_MODE execution
                txn.retry_count += 1
                order_id = order_result.get("id")

                if not order_id or order_result.get("status") == "failed":
                    error_msg = order_result.get("error", "Razorpay Test Order creation failed: No order ID returned")
                    txn.status = "FAILED"
                    execution_result["status"] = "FAILED"
                    execution_result["recovered_amount"] = 0.0
                    execution_result["message"] = f"Razorpay Test Order creation failed ({error_msg})."

                    action_rec = RecoveryAction(
                        id=f"act_{uuid.uuid4().hex[:12]}",
                        transaction_id=txn.id,
                        action_type=policy_res.action,
                        status="FAILED",
                        ai_diagnosis=ai_analysis.diagnosis,
                        ai_probability=ai_analysis.recovery_probability,
                        ai_risk_level=ai_analysis.risk_level,
                        ai_reasoning=ai_analysis.reason,
                        policy_allowed=True,
                        policy_reasons_json=json.dumps(policy_res.reasons),
                        requires_human_approval=False,
                        recovered_amount=0.0,
                        execution_details_json=json.dumps({"order_result": order_result, "error": str(error_msg)}),
                        mode="TEST_MODE",
                        created_at=now + timedelta(milliseconds=500),
                        executed_at=now + timedelta(milliseconds=700)
                    )
                    db.add(action_rec)
                else:
                    txn.razorpay_order_id = order_id
                    execution_result["razorpay_order_id"] = order_id
                    payments = await razorpay_service.fetch_order_payments(order_id)
                    is_captured = any(p.get("status") == "captured" for p in payments)

                    if is_captured:
                        captured_pay = next(p for p in payments if p.get("status") == "captured")
                        txn.status = "RECOVERED"
                        txn.razorpay_payment_id = captured_pay.get("id")
                        execution_result["status"] = "SUCCESS"
                        execution_result["recovered_amount"] = txn.amount
                        execution_result["message"] = f"Razorpay Test payment verified and captured ({captured_pay.get('id')}). Revenue captured."

                        action_rec = RecoveryAction(
                            id=f"act_{uuid.uuid4().hex[:12]}",
                            transaction_id=txn.id,
                            action_type=policy_res.action,
                            status="SUCCESS",
                            ai_diagnosis=ai_analysis.diagnosis,
                            ai_probability=ai_analysis.recovery_probability,
                            ai_risk_level=ai_analysis.risk_level,
                            ai_reasoning=ai_analysis.reason,
                            policy_allowed=True,
                            policy_reasons_json=json.dumps(policy_res.reasons),
                            requires_human_approval=False,
                            recovered_amount=txn.amount,
                            execution_details_json=json.dumps({"payment_id": captured_pay.get("id"), "order_id": order_id, "status": "captured"}),
                            mode="TEST_MODE",
                            created_at=now + timedelta(milliseconds=500),
                            executed_at=now + timedelta(milliseconds=700)
                        )
                        db.add(action_rec)

                        aud_succ = AuditEvent(
                            id=f"aud_{uuid.uuid4().hex[:12]}",
                            timestamp=now + timedelta(milliseconds=700),
                            transaction_id=txn.id,
                            event_type="PAYMENT_RECOVERED",
                            actor="RAZORPAY_GATEWAY",
                            decision="REVENUE_RECOVERED",
                            details_json=json.dumps({
                                "recovered_amount": txn.amount,
                                "payment_id": captured_pay.get("id"),
                                "order_id": order_id,
                                "mode": "TEST_MODE",
                                "action": policy_res.action
                            })
                        )
                        db.add(aud_succ)

                    else:
                        txn.status = "RECOVERY_PENDING"
                        execution_result["status"] = "PENDING"
                        execution_result["recovered_amount"] = 0.0
                        execution_result["message"] = f"Razorpay Test Order created ({order_id}). Awaiting customer test payment authorization."

                        action_rec = RecoveryAction(
                            id=f"act_{uuid.uuid4().hex[:12]}",
                            transaction_id=txn.id,
                            action_type=policy_res.action,
                            status="PENDING",
                            ai_diagnosis=ai_analysis.diagnosis,
                            ai_probability=ai_analysis.recovery_probability,
                            ai_risk_level=ai_analysis.risk_level,
                            ai_reasoning=ai_analysis.reason,
                            policy_allowed=True,
                            policy_reasons_json=json.dumps(policy_res.reasons),
                            requires_human_approval=False,
                            recovered_amount=0.0,
                            execution_details_json=json.dumps({"order_id": order_id, "mode": "TEST_MODE"}),
                            mode="TEST_MODE",
                            created_at=now + timedelta(milliseconds=500)
                        )
                        aud_pending = AuditEvent(
                            id=f"aud_{uuid.uuid4().hex[:12]}",
                            timestamp=now + timedelta(milliseconds=700),
                            transaction_id=txn.id,
                            event_type="RECOVERY_ACTION_TRIGGERED",
                            actor="RAZORPAY_GATEWAY",
                            decision="TEST_ORDER_DISPATCHED",
                            details_json=json.dumps({
                                "order_id": order_id,
                                "mode": "TEST_MODE",
                                "action": policy_res.action,
                                "retry_count": txn.retry_count
                            })
                        )
                        db.add(aud_pending)

        elif policy_res.action == "PAYMENT_LINK":
            # Generate payment link via Razorpay
            plink = await razorpay_service.create_payment_link(
                amount_in_inr=txn.amount,
                customer_name=customer.name,
                customer_email=customer.email,
                customer_phone=customer.phone,
                description=f"Recovered Order {order_result.get('id') or txn.id}",
                force_mode=exec_mode
            )
            plink_url = plink.get("short_url")

            if exec_mode == "TEST_MODE" and (not plink_url or plink.get("status") == "failed"):
                error_msg = plink.get("error", "Razorpay Payment Link creation failed")
                txn.status = "FAILED"
                execution_result["status"] = "FAILED"
                execution_result["recovered_amount"] = 0.0
                execution_result["message"] = f"Razorpay Payment Link creation failed ({error_msg})."

                action_rec = RecoveryAction(
                    id=f"act_{uuid.uuid4().hex[:12]}",
                    transaction_id=txn.id,
                    action_type="PAYMENT_LINK",
                    status="FAILED",
                    ai_diagnosis=ai_analysis.diagnosis,
                    ai_probability=ai_analysis.recovery_probability,
                    ai_risk_level=ai_analysis.risk_level,
                    ai_reasoning=ai_analysis.reason,
                    policy_allowed=True,
                    policy_reasons_json=json.dumps(policy_res.reasons),
                    requires_human_approval=False,
                    recovered_amount=0.0,
                    execution_details_json=json.dumps({"payment_link": plink, "error": str(error_msg)}),
                    mode=exec_mode,
                    created_at=now + timedelta(milliseconds=500),
                    executed_at=now + timedelta(milliseconds=700)
                )
                db.add(action_rec)
            else:
                txn.status = "RECOVERY_PENDING"
                txn.razorpay_payment_link = plink_url
                execution_result["status"] = "PENDING"
                execution_result["recovered_amount"] = 0.0
                execution_result["razorpay_payment_link"] = plink_url
                execution_result["message"] = f"Generated Razorpay Payment Link ({plink_url}). Sent to customer {customer.email}."

                action_rec = RecoveryAction(
                    id=f"act_{uuid.uuid4().hex[:12]}",
                    transaction_id=txn.id,
                    action_type="PAYMENT_LINK",
                    status="PENDING",
                    ai_diagnosis=ai_analysis.diagnosis,
                    ai_probability=ai_analysis.recovery_probability,
                    ai_risk_level=ai_analysis.risk_level,
                    ai_reasoning=ai_analysis.reason,
                    policy_allowed=True,
                    policy_reasons_json=json.dumps(policy_res.reasons),
                    requires_human_approval=False,
                    recovered_amount=0.0,
                    execution_details_json=json.dumps(plink),
                    mode=exec_mode,
                    created_at=now + timedelta(milliseconds=500),
                    executed_at=now + timedelta(milliseconds=700)
                )
                db.add(action_rec)

            aud_link = AuditEvent(
                id=f"aud_{uuid.uuid4().hex[:12]}",
                timestamp=now + timedelta(milliseconds=700),
                transaction_id=txn.id,
                event_type="RECOVERY_ACTION_TRIGGERED",
                actor="RAZORPAY_GATEWAY",
                decision="PAYMENT_LINK_DISPATCHED",
                details_json=json.dumps({"short_url": plink.get("short_url"), "mode": exec_mode, "retry_count": txn.retry_count})
            )
            db.add(aud_link)

    # Ensure complete consistency between transaction.retry_count, policy_res, and aud_policy
    for r in policy_res.rules_evaluated:
        if r.rule_id == "RULE_MAX_RETRIES":
            if r.passed:
                r.reason = f"Current retries ({txn.retry_count}) is within limit (2)."
            else:
                r.reason = f"Exceeded maximum automated retry limit (2 allowed, {txn.retry_count} attempted). Action overridden to STOP."
    policy_res.reasons = [
        f"Current retries ({txn.retry_count}) is within limit (2)." if "Current retries (" in r
        else (f"Exceeded maximum automated retry limit (2 allowed, {txn.retry_count} attempted). Action overridden to STOP." if "Exceeded maximum automated retry limit" in r else r)
        for r in policy_res.reasons
    ]
    aud_policy.details_json = json.dumps({
        "action": policy_res.action,
        "allowed": policy_res.allowed,
        "requires_human_approval": policy_res.requires_human_approval,
        "reasons": policy_res.reasons,
        "rules_count": len(policy_res.rules_evaluated),
        "retry_count": txn.retry_count
    })

    db.commit()
    db.refresh(txn)

    # Fetch audit events for this run
    events = db.query(AuditEvent).filter(AuditEvent.transaction_id == txn.id).order_by(AuditEvent.timestamp).all()

    return {
        "scenario_id": scenario_key,
        "title": spec["title"],
        "transaction": txn.to_dict(include_relations=True),
        "ai_analysis": ai_analysis.model_dump(),
        "policy_decision": policy_res.model_dump(),
        "recovery_result": execution_result,
        "audit_timeline": [e.to_dict() for e in events],
        "mode": exec_mode
    }

@router.post("/payment")
async def create_demo_payment(request: DemoPaymentRequest, db: Session = Depends(get_db)):
    """
    Creates an on-demand test payment transaction and runs the recovery workflow.
    """
    spec_key = "temporary_upi_failure"
    if request.failure_reason == "BANK_DECLINED":
        spec_key = "bank_decline"
    elif request.failure_reason == "NETWORK_ERROR":
        spec_key = "network_failure"
    elif request.failure_reason == "INSUFFICIENT_FUNDS":
        spec_key = "insufficient_funds"

    return await run_scenario(DemoScenarioRequest(scenario=spec_key), db=db)

