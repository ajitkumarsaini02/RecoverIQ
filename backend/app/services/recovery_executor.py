import uuid
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models import Transaction, Customer, RecoveryAction, AuditEvent
from app.services.razorpay_service import razorpay_service
from app.services.ai_agent import ai_agent, AIAgentRecommendation
from app.services.policy_engine import policy_engine, PolicyEvaluationResult
from app.services.audit_service import audit_service

logger = logging.getLogger("recoveriq.recovery_executor")

class RecoveryExecutionResponse(BaseModel):
    transaction_id: str
    action: str
    status: str = Field(description="SUCCESS, FAILED, PENDING, STOPPED, REQUIRES_APPROVAL")
    amount_recovered: float = 0.0
    timestamp: str
    mode: str = "DEMO_MODE"
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    ai_diagnosis: Optional[str] = None
    ai_probability: Optional[float] = None
    policy_reason: Optional[str] = None

class RecoveryExecutionService:
    """
    Execution engine that safely executes policy-authorized recovery actions:
    Failed Payment -> AI Analysis -> Policy Validation -> Recovery Action -> Result.
    """

    async def execute_recovery(
        self, 
        db: Session, 
        transaction: Transaction,
        mode: Optional[str] = None
    ) -> RecoveryExecutionResponse:
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # Idempotency Guard 1: Already recovered
        if transaction.status == "RECOVERED":
            return RecoveryExecutionResponse(
                transaction_id=transaction.id,
                action="NONE",
                status="SUCCESS",
                amount_recovered=transaction.amount,
                timestamp=now_iso,
                mode=mode or razorpay_service.current_mode_label,
                message="Transaction has already been successfully recovered (Idempotent response).",
                details={"already_recovered": True, "idempotent": True}
            )

        # Idempotency Guard 2: Prevent rapid back-to-back click race condition (within 5 seconds)
        if transaction.last_recovery_attempt_at:
            delta_seconds = (now - transaction.last_recovery_attempt_at.replace(tzinfo=timezone.utc)).total_seconds()
            if delta_seconds < 5.0 and transaction.status in ["RECOVERY_PENDING", "APPROVAL_REQUIRED"]:
                return RecoveryExecutionResponse(
                    transaction_id=transaction.id,
                    action="COOLDOWN",
                    status="PENDING",
                    amount_recovered=0.0,
                    timestamp=now_iso,
                    mode=mode or razorpay_service.current_mode_label,
                    message="Recovery is already being processed. Please wait for previous action to finalize.",
                    details={"in_progress": True, "cooldown_remaining": round(5.0 - delta_seconds, 1)}
                )

        customer = transaction.customer
        current_mode = mode or ("TEST_MODE" if razorpay_service.is_live_test_mode else "SIMULATION_MODE")

        # 1. AI Analysis (Failure diagnosis + customer context)
        ai_recommendation = ai_agent.analyze_failure(transaction=transaction, customer=customer)

        # Audit: FAILURE_ANALYZED
        audit_service.log_failure_analyzed(
            db=db,
            transaction_id=transaction.id,
            diagnosis=ai_recommendation.diagnosis,
            failure_reason=transaction.failure_reason
        )

        # Audit: CUSTOMER_CONTEXT_ANALYZED
        cust_id = customer.id if customer else transaction.customer_id
        cust_ltv = customer.lifetime_value if customer else transaction.customer_lifetime_value
        succ_cnt = customer.successful_payments_count if customer else transaction.previous_successful_payments
        fail_cnt = customer.failed_payments_count if customer else transaction.previous_failed_payments
        audit_service.log_customer_context_analyzed(
            db=db,
            transaction_id=transaction.id,
            customer_id=cust_id,
            customer_ltv=cust_ltv,
            successful_payments=succ_cnt,
            failed_payments=fail_cnt
        )

        # Audit: AI_RECOMMENDATION
        audit_service.log_ai_recommendation(
            db=db,
            transaction_id=transaction.id,
            action=ai_recommendation.recommended_action,
            probability=ai_recommendation.recovery_probability,
            risk_level=ai_recommendation.risk_level,
            reason=ai_recommendation.reason
        )

        # 2. Deterministic Policy Validation
        policy_res = policy_engine.evaluate(transaction=transaction, recommendation=ai_recommendation)

        # Audit: POLICY_VALIDATED
        audit_service.log_policy_validated(
            db=db,
            transaction_id=transaction.id,
            allowed=policy_res.allowed,
            action=policy_res.action,
            requires_human_approval=policy_res.requires_human_approval,
            reason=policy_res.reason
        )

        # 3. Check Policy Rejections / Stop Conditions
        if not policy_res.allowed or policy_res.action == "STOP":
            transaction.status = "STOPPED"
            transaction.updated_at = now

            action_record = RecoveryAction(
                id=f"act_{uuid.uuid4().hex[:12]}",
                transaction_id=transaction.id,
                action_type="STOP",
                status="REJECTED",
                ai_diagnosis=ai_recommendation.diagnosis,
                ai_probability=ai_recommendation.recovery_probability,
                ai_risk_level=ai_recommendation.risk_level,
                ai_reasoning=ai_recommendation.reason,
                policy_allowed=False,
                policy_reasons_json=json.dumps(policy_res.reasons),
                requires_human_approval=False,
                recovered_amount=0.0,
                mode=current_mode,
                created_at=now,
                executed_at=now
            )
            db.add(action_record)

            # Audit: RECOVERY_STOPPED
            audit_service.log_recovery_stopped(
                db=db,
                transaction_id=transaction.id,
                reason=policy_res.reason
            )
            db.commit()

            return RecoveryExecutionResponse(
                transaction_id=transaction.id,
                action="STOP",
                status="STOPPED",
                amount_recovered=0.0,
                timestamp=now_iso,
                mode=current_mode,
                message=f"Recovery halted by Policy Guardrail: {policy_res.reason}",
                details={"policy_allowed": False},
                ai_diagnosis=ai_recommendation.diagnosis,
                ai_probability=ai_recommendation.recovery_probability,
                policy_reason=policy_res.reason
            )

        # 4. Check Human Approval Gate
        if policy_res.requires_human_approval:
            transaction.status = "APPROVAL_REQUIRED"
            transaction.updated_at = now

            action_record = RecoveryAction(
                id=f"act_{uuid.uuid4().hex[:12]}",
                transaction_id=transaction.id,
                action_type=policy_res.action,
                status="PENDING_APPROVAL",
                ai_diagnosis=ai_recommendation.diagnosis,
                ai_probability=ai_recommendation.recovery_probability,
                ai_risk_level=ai_recommendation.risk_level,
                ai_reasoning=ai_recommendation.reason,
                policy_allowed=policy_res.allowed,
                policy_reasons_json=json.dumps(policy_res.reasons),
                requires_human_approval=True,
                recovered_amount=0.0,
                mode=current_mode,
                created_at=now
            )
            db.add(action_record)

            # Audit: APPROVAL_REQUESTED
            audit_service.log_approval_requested(
                db=db,
                transaction_id=transaction.id,
                action_id=action_record.id,
                amount=transaction.amount,
                reason=policy_res.reason
            )
            db.commit()

            return RecoveryExecutionResponse(
                transaction_id=transaction.id,
                action=policy_res.action,
                status="REQUIRES_APPROVAL",
                amount_recovered=0.0,
                timestamp=now_iso,
                mode=current_mode,
                message=f"High-value or high-risk recovery action gated for human approval: {policy_res.reason}",
                details={"action_id": action_record.id, "requires_human_approval": True},
                ai_diagnosis=ai_recommendation.diagnosis,
                ai_probability=ai_recommendation.recovery_probability,
                policy_reason=policy_res.reason
            )

        # 5. Policy Allowed: Execute Recovery Action
        action_type = policy_res.action

        # Audit: RECOVERY_EXECUTED
        audit_service.log_recovery_executed(
            db=db,
            transaction_id=transaction.id,
            action=action_type,
            mode=current_mode
        )

        if action_type in ["RETRY_PAYMENT", "ALTERNATIVE_PAYMENT_METHOD"]:
            try:
                # Create Razorpay Test Order
                order_data = await razorpay_service.create_order(
                    amount_in_inr=transaction.amount,
                    receipt=f"rcpt_recov_{uuid.uuid4().hex[:6]}",
                    force_mode=current_mode
                )

                transaction.retry_count += 1
                transaction.last_recovery_attempt_at = now
                transaction.razorpay_order_id = order_data.get("id")
                transaction.updated_at = now

                # In SIMULATION_MODE: simulate capture
                if current_mode == "SIMULATION_MODE":
                    transaction.status = "RECOVERED"
                    recovered_amount = transaction.amount
                    sim_pay_id = f"pay_sim_{uuid.uuid4().hex[:10]}"
                    transaction.razorpay_payment_id = sim_pay_id

                    action_record = RecoveryAction(
                        id=f"act_{uuid.uuid4().hex[:12]}",
                        transaction_id=transaction.id,
                        action_type=action_type,
                        status="SUCCESS",
                        ai_diagnosis=ai_recommendation.diagnosis,
                        ai_probability=ai_recommendation.recovery_probability,
                        ai_risk_level=ai_recommendation.risk_level,
                        ai_reasoning=ai_recommendation.reason,
                        policy_allowed=True,
                        policy_reasons_json=json.dumps(policy_res.reasons),
                        requires_human_approval=False,
                        recovered_amount=recovered_amount,
                        execution_details_json=json.dumps({"order_id": order_data.get("id"), "payment_id": sim_pay_id, "mode": "SIMULATION_MODE"}),
                        mode="SIMULATION_MODE",
                        created_at=now,
                        executed_at=now
                    )
                    db.add(action_record)

                    audit_service.log_payment_recovered(
                        db=db,
                        transaction_id=transaction.id,
                        amount_recovered=recovered_amount,
                        payment_id=sim_pay_id,
                        mode="SIMULATION_MODE"
                    )
                    db.commit()

                    return RecoveryExecutionResponse(
                        transaction_id=transaction.id,
                        action=action_type,
                        status="SUCCESS",
                        amount_recovered=recovered_amount,
                        timestamp=now_iso,
                        mode="SIMULATION_MODE",
                        message=f"Simulated payment retry executed successfully. Revenue recovered: ₹{transaction.amount:,.0f}",
                        details={"order_id": order_data.get("id"), "payment_id": sim_pay_id, "simulated": True},
                        ai_diagnosis=ai_recommendation.diagnosis,
                        ai_probability=ai_recommendation.recovery_probability,
                        policy_reason=policy_res.reason
                    )

                # In TEST_MODE: Real Razorpay Test Order created.
                # Check if payment was immediately verified or remains pending customer checkout.
                payments = await razorpay_service.fetch_order_payments(order_data.get("id", ""))
                is_captured = any(p.get("status") == "captured" for p in payments)

                if is_captured:
                    captured_pay = next(p for p in payments if p.get("status") == "captured")
                    transaction.status = "RECOVERED"
                    transaction.razorpay_payment_id = captured_pay.get("id")
                    recovered_amount = float(captured_pay.get("amount", 0)) / 100.0

                    action_record = RecoveryAction(
                        id=f"act_{uuid.uuid4().hex[:12]}",
                        transaction_id=transaction.id,
                        action_type=action_type,
                        status="SUCCESS",
                        ai_diagnosis=ai_recommendation.diagnosis,
                        ai_probability=ai_recommendation.recovery_probability,
                        ai_risk_level=ai_recommendation.risk_level,
                        ai_reasoning=ai_recommendation.reason,
                        policy_allowed=True,
                        policy_reasons_json=json.dumps(policy_res.reasons),
                        requires_human_approval=False,
                        recovered_amount=recovered_amount,
                        execution_details_json=json.dumps({"order_id": order_data.get("id"), "payment_id": captured_pay.get("id"), "mode": "TEST_MODE"}),
                        mode="TEST_MODE",
                        created_at=now,
                        executed_at=now
                    )
                    db.add(action_record)

                    audit_service.log_payment_recovered(
                        db=db,
                        transaction_id=transaction.id,
                        amount_recovered=recovered_amount,
                        payment_id=captured_pay.get("id"),
                        mode="TEST_MODE"
                    )
                    db.commit()

                    return RecoveryExecutionResponse(
                        transaction_id=transaction.id,
                        action=action_type,
                        status="SUCCESS",
                        amount_recovered=recovered_amount,
                        timestamp=now_iso,
                        mode="TEST_MODE",
                        message=f"Razorpay Test Payment verified and captured. Revenue captured: ₹{recovered_amount:,.0f}",
                        details={"order_id": order_data.get("id"), "payment_id": captured_pay.get("id"), "verified": True},
                        ai_diagnosis=ai_recommendation.diagnosis,
                        ai_probability=ai_recommendation.recovery_probability,
                        policy_reason=policy_res.reason
                    )
                else:
                    # Order is created and awaiting payment capture
                    transaction.status = "RECOVERY_PENDING"
                    recovered_amount = 0.0

                    action_record = RecoveryAction(
                        id=f"act_{uuid.uuid4().hex[:12]}",
                        transaction_id=transaction.id,
                        action_type=action_type,
                        status="PENDING",
                        ai_diagnosis=ai_recommendation.diagnosis,
                        ai_probability=ai_recommendation.recovery_probability,
                        ai_risk_level=ai_recommendation.risk_level,
                        ai_reasoning=ai_recommendation.reason,
                        policy_allowed=True,
                        policy_reasons_json=json.dumps(policy_res.reasons),
                        requires_human_approval=False,
                        recovered_amount=0.0,
                        execution_details_json=json.dumps({"order_id": order_data.get("id"), "mode": "TEST_MODE", "status": "order_created"}),
                        mode="TEST_MODE",
                        created_at=now
                    )
                    db.add(action_record)
                    db.commit()

                    return RecoveryExecutionResponse(
                        transaction_id=transaction.id,
                        action=action_type,
                        status="PENDING",
                        amount_recovered=0.0,
                        timestamp=now_iso,
                        mode="TEST_MODE",
                        message=f"Razorpay Test Order created ({order_data.get('id')}). Awaiting payment verification or webhook.",
                        details={"order_id": order_data.get("id"), "verified": False, "pending_payment": True},
                        ai_diagnosis=ai_recommendation.diagnosis,
                        ai_probability=ai_recommendation.recovery_probability,
                        policy_reason=policy_res.reason
                    )

            except Exception as e:
                logger.error(f"Recovery execution failed: {e}")
                transaction.status = "FAILED"
                transaction.retry_count += 1
                transaction.updated_at = now

                action_record = RecoveryAction(
                    id=f"act_{uuid.uuid4().hex[:12]}",
                    transaction_id=transaction.id,
                    action_type=action_type,
                    status="FAILED",
                    ai_diagnosis=ai_recommendation.diagnosis,
                    ai_probability=ai_recommendation.recovery_probability,
                    ai_risk_level=ai_recommendation.risk_level,
                    ai_reasoning=ai_recommendation.reason,
                    policy_allowed=True,
                    policy_reasons_json=json.dumps(policy_res.reasons),
                    requires_human_approval=False,
                    recovered_amount=0.0,
                    execution_details_json=json.dumps({"error": str(e)}),
                    mode=current_mode,
                    created_at=now,
                    executed_at=now
                )
                db.add(action_record)

                audit_service.log_recovery_failed(
                    db=db,
                    transaction_id=transaction.id,
                    error_message=str(e)
                )
                db.commit()

                return RecoveryExecutionResponse(
                    transaction_id=transaction.id,
                    action=action_type,
                    status="FAILED",
                    amount_recovered=0.0,
                    timestamp=now_iso,
                    mode=current_mode,
                    message=f"Recovery attempt failed: {str(e)}",
                    details={"error": str(e)},
                    ai_diagnosis=ai_recommendation.diagnosis,
                    ai_probability=ai_recommendation.recovery_probability,
                    policy_reason=policy_res.reason
                )

        elif action_type == "PAYMENT_LINK":
            cust_name = customer.name if customer else (transaction.customer_name or "Valued Customer")
            cust_email = customer.email if customer else (transaction.customer_email or "customer@domain.in")
            cust_phone = customer.phone if customer else "+919876543210"

            plink = await razorpay_service.create_payment_link(
                amount_in_inr=transaction.amount,
                customer_name=cust_name,
                customer_email=cust_email,
                customer_phone=cust_phone,
                description=f"RecoverIQ Payment Link for Txn {transaction.id}",
                force_mode=current_mode
            )

            transaction.status = "RECOVERY_PENDING"
            transaction.razorpay_payment_link = plink.get("short_url")
            transaction.updated_at = now

            action_record = RecoveryAction(
                id=f"act_{uuid.uuid4().hex[:12]}",
                transaction_id=transaction.id,
                action_type="PAYMENT_LINK",
                status="PENDING",
                ai_diagnosis=ai_recommendation.diagnosis,
                ai_probability=ai_recommendation.recovery_probability,
                ai_risk_level=ai_recommendation.risk_level,
                ai_reasoning=ai_recommendation.reason,
                policy_allowed=True,
                policy_reasons_json=json.dumps(policy_res.reasons),
                requires_human_approval=False,
                recovered_amount=0.0,
                execution_details_json=json.dumps(plink),
                mode=current_mode,
                created_at=now
            )
            db.add(action_record)
            db.commit()

            return RecoveryExecutionResponse(
                transaction_id=transaction.id,
                action="PAYMENT_LINK",
                status="PENDING",
                amount_recovered=0.0,
                timestamp=now_iso,
                mode=current_mode,
                message=f"Razorpay Payment Link generated ({plink.get('short_url')}). Awaiting customer payment.",
                details={"payment_link": plink.get("short_url"), "link_id": plink.get("id"), "verified": False},
                ai_diagnosis=ai_recommendation.diagnosis,
                ai_probability=ai_recommendation.recovery_probability,
                policy_reason=policy_res.reason
            )

        elif action_type == "REMINDER":
            transaction.status = "RECOVERY_PENDING"
            transaction.updated_at = now

            action_record = RecoveryAction(
                id=f"act_{uuid.uuid4().hex[:12]}",
                transaction_id=transaction.id,
                action_type="REMINDER",
                status="SUCCESS",
                ai_diagnosis=ai_recommendation.diagnosis,
                ai_probability=ai_recommendation.recovery_probability,
                ai_risk_level=ai_recommendation.risk_level,
                ai_reasoning=ai_recommendation.reason,
                policy_allowed=True,
                policy_reasons_json=json.dumps(policy_res.reasons),
                requires_human_approval=False,
                recovered_amount=0.0,
                execution_details_json=json.dumps({"scheduled_reminder": True}),
                mode=current_mode,
                created_at=now,
                executed_at=now
            )
            db.add(action_record)
            db.commit()

            return RecoveryExecutionResponse(
                transaction_id=transaction.id,
                action="REMINDER",
                status="PENDING",
                amount_recovered=0.0,
                timestamp=now_iso,
                mode=current_mode,
                message="Scheduled gentle customer reminder for retry checkout.",
                details={"reminder_scheduled": True},
                ai_diagnosis=ai_recommendation.diagnosis,
                ai_probability=ai_recommendation.recovery_probability,
                policy_reason=policy_res.reason
            )

        # Fallback
        return RecoveryExecutionResponse(
            transaction_id=transaction.id,
            action=action_type,
            status="PENDING",
            amount_recovered=0.0,
            timestamp=now_iso,
            mode=current_mode,
            message="Recovery action initiated.",
            details={},
            ai_diagnosis=ai_recommendation.diagnosis,
            ai_probability=ai_recommendation.recovery_probability,
            policy_reason=policy_res.reason
        )

        # Fallback
        return RecoveryExecutionResponse(
            transaction_id=transaction.id,
            action=action_type,
            status="PENDING",
            amount_recovered=0.0,
            timestamp=now_iso,
            mode=current_mode,
            message="Recovery action initiated.",
            details={},
            ai_diagnosis=ai_recommendation.diagnosis,
            ai_probability=ai_recommendation.recovery_probability,
            policy_reason=policy_res.reason
        )

recovery_executor = RecoveryExecutionService()
