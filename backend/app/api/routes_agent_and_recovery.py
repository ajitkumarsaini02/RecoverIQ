import uuid
import json
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import Optional, List
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models import Transaction, Customer, RecoveryAction, AuditEvent
from app.services.razorpay_service import razorpay_service
from app.services.audit_service import audit_service
from app.services.ai_agent import ai_agent
from app.services.policy_engine import policy_engine
from app.services.recovery_executor import recovery_executor, RecoveryExecutionResponse
from app.schemas.transaction import AuditEventSchema, RecoveryActionSchema

router = APIRouter(prefix="/api", tags=["Agent & Recovery Operations"])

class RejectRequest(BaseModel):
    reason: Optional[str] = "Merchant rejected action manually"

@router.post("/agent/analyze/{transaction_id}")
def analyze_transaction_by_id(transaction_id: str, db: Session = Depends(get_db)):
    """Run AI diagnosis and probability estimation on a specific transaction."""
    txn = db.query(Transaction).options(joinedload(Transaction.customer)).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    recommendation = ai_agent.analyze_failure(transaction=txn, customer=txn.customer)
    policy_res = policy_engine.evaluate(transaction=txn, recommendation=recommendation)

    # Log AI analysis event
    aud = AuditEvent(
        id=f"aud_{uuid.uuid4().hex[:12]}",
        timestamp=datetime.now(timezone.utc),
        transaction_id=txn.id,
        event_type="AI_ANALYSIS_COMPLETED",
        actor="AI_AGENT",
        decision=recommendation.recommended_action,
        details_json=json.dumps({
            "diagnosis": recommendation.diagnosis,
            "recovery_probability": recommendation.recovery_probability,
            "risk_level": recommendation.risk_level,
            "policy_allowed": policy_res.allowed,
            "requires_human_approval": policy_res.requires_human_approval
        })
    )
    db.add(aud)
    db.commit()

    return {
        "transaction_id": txn.id,
        "ai_recommendation": recommendation.model_dump(),
        "policy_decision": policy_res.model_dump()
    }

@router.post("/recovery/execute/{transaction_id}", response_model=RecoveryExecutionResponse)
async def execute_recovery_for_transaction(
    transaction_id: str, 
    mode: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Executes the 5-step recovery workflow:
    Failed Payment -> AI Analysis -> Policy Validation -> Recovery Action -> Result
    """
    txn = db.query(Transaction).options(joinedload(Transaction.customer)).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction with ID '{transaction_id}' not found.")

    result = await recovery_executor.execute_recovery(db=db, transaction=txn, mode=mode)
    return result

@router.get("/approvals")
def list_pending_approvals(db: Session = Depends(get_db)):
    """Fetch pending recovery actions waiting for human merchant approval."""
    actions = db.query(RecoveryAction).options(
        joinedload(RecoveryAction.transaction).joinedload(Transaction.customer)
    ).filter(
        RecoveryAction.status == "PENDING_APPROVAL"
    ).order_by(desc(RecoveryAction.created_at)).all()

    results = []
    for act in actions:
        results.append({
            "id": act.id,
            "transaction_id": act.transaction_id,
            "transaction": act.transaction.to_dict(include_relations=True) if act.transaction else None,
            "action_type": act.action_type,
            "ai_diagnosis": act.ai_diagnosis,
            "ai_probability": act.ai_probability,
            "ai_risk_level": act.ai_risk_level,
            "ai_reasoning": act.ai_reasoning,
            "policy_decision": {
                "allowed": act.policy_allowed,
                "requires_human_approval": act.requires_human_approval,
                "reasons": json.loads(act.policy_reasons_json) if act.policy_reasons_json else []
            },
            "policy_reasons": json.loads(act.policy_reasons_json) if act.policy_reasons_json else [],
            "mode": act.mode,
            "created_at": act.created_at.isoformat() if act.created_at else None
        })

    return results

@router.post("/recovery/approve/{action_id}")
async def approve_action(action_id: str, db: Session = Depends(get_db)):
    """Approve a gated recovery action and attempt authorized recovery execution."""
    act = db.query(RecoveryAction).options(joinedload(RecoveryAction.transaction).joinedload(Transaction.customer)).filter(RecoveryAction.id == action_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="Recovery action not found")

    if act.status != "PENDING_APPROVAL":
        raise HTTPException(
            status_code=400,
            detail=f"Action cannot be approved. Current status: '{act.status}' (must be PENDING_APPROVAL)."
        )

    now = datetime.now(timezone.utc)
    act.approved_by = "Merchant Operator"
    act.approved_at = now
    act.executed_at = now

    # Log APPROVED Audit Event (Human authorization)
    aud_app = AuditEvent(
        id=f"aud_{uuid.uuid4().hex[:12]}",
        timestamp=now,
        transaction_id=act.transaction_id,
        event_type="APPROVED",
        actor="HUMAN_OPERATOR",
        decision="ACTION_APPROVED",
        details_json=json.dumps({"action_id": act.id, "action_type": act.action_type, "approved_by": "Merchant Operator"})
    )
    db.add(aud_app)

    # Perform authorized recovery execution
    txn = act.transaction
    if act.mode == "SIMULATION_MODE":
        act.status = "SUCCESS"
        act.recovered_amount = txn.amount if txn else 0.0
        if txn:
            txn.status = "RECOVERED"
            txn.retry_count += 1
            txn.updated_at = now

        aud_rec = AuditEvent(
            id=f"aud_{uuid.uuid4().hex[:12]}",
            timestamp=now + timedelta(milliseconds=100),
            transaction_id=act.transaction_id,
            event_type="PAYMENT_RECOVERED",
            actor="RAZORPAY_GATEWAY",
            decision="REVENUE_RECOVERED",
            details_json=json.dumps({"recovered_amount": act.recovered_amount, "mode": "SIMULATION_MODE"})
        )
        db.add(aud_rec)
        db.commit()

        return {
            "status": "APPROVED_AND_EXECUTED",
            "action_id": act.id,
            "recovered_amount": act.recovered_amount,
            "message": f"Approved and simulated recovery of ₹{act.recovered_amount:,.0f}"
        }
    else:
        # Real Test Mode: generate payment link or create order
        if txn:
            txn.retry_count += 1
            txn.status = "RECOVERY_PENDING"
            txn.updated_at = now

        from app.services.razorpay_service import razorpay_service
        plink = await razorpay_service.create_payment_link(
            amount_in_inr=txn.amount if txn else 1000.0,
            customer_name=txn.customer.name if (txn and txn.customer) else "Enterprise Customer",
            customer_email=txn.customer.email if (txn and txn.customer) else "customer@domain.in",
            customer_phone=txn.customer.phone if (txn and txn.customer) else "+919876543210",
            description=f"Approved Enterprise Recovery - Txn {txn.id if txn else 'N/A'}",
            force_mode="TEST_MODE"
        )
        act.status = "APPROVED"
        act.recovered_amount = 0.0
        act.execution_details_json = json.dumps(plink)
        if txn:
            txn.razorpay_payment_link = plink.get("short_url")

        db.commit()

        return {
            "status": "APPROVED_AND_DISPATCHED",
            "action_id": act.id,
            "payment_link": plink.get("short_url"),
            "recovered_amount": 0.0,
            "message": f"Approved! Razorpay Test Payment Link generated ({plink.get('short_url')}). Awaiting customer payment."
        }

@router.post("/recovery/reject/{action_id}")
def reject_action(action_id: str, req: Optional[RejectRequest] = None, db: Session = Depends(get_db)):
    """Reject a gated recovery action and halt recovery."""
    act = db.query(RecoveryAction).options(joinedload(RecoveryAction.transaction)).filter(RecoveryAction.id == action_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="Recovery action not found")

    if act.status != "PENDING_APPROVAL":
        raise HTTPException(
            status_code=400,
            detail=f"Action cannot be rejected. Current status: '{act.status}' (must be PENDING_APPROVAL)."
        )

    rejection_reason = req.reason if req and req.reason else "Merchant manually rejected recovery"
    now = datetime.now(timezone.utc)
    act.status = "REJECTED"
    act.rejection_reason = rejection_reason
    act.executed_at = now

    if act.transaction:
        act.transaction.status = "STOPPED"
        act.transaction.updated_at = now

    # Log REJECTED Audit Event
    aud = AuditEvent(
        id=f"aud_{uuid.uuid4().hex[:12]}",
        timestamp=now,
        transaction_id=act.transaction_id,
        event_type="REJECTED",
        actor="HUMAN_OPERATOR",
        decision="ACTION_REJECTED",
        details_json=json.dumps({"action_id": act.id, "reason": rejection_reason})
    )
    db.add(aud)
    db.commit()

    return {
        "status": "REJECTED",
        "action_id": act.id,
        "message": f"Action rejected: {rejection_reason}"
    }

class VerifyPaymentRequest(BaseModel):
    payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None

@router.post("/recovery/verify/{id_or_token}")
async def verify_transaction_payment(
    id_or_token: str,
    req: Optional[VerifyPaymentRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Independently verifies captured payment status on Razorpay Test API.
    Guarantees that a transaction is transitioned to RECOVERED only if Razorpay confirms capture.
    """
    # Check if id_or_token is an action_id
    if id_or_token.startswith("act_"):
        action = db.query(RecoveryAction).filter(RecoveryAction.id == id_or_token).first()
        if not action:
            raise HTTPException(status_code=404, detail="Recovery action not found")
        transaction_id = action.transaction_id
    else:
        transaction_id = id_or_token

    # Query transaction with database locking where supported (PostgreSQL)
    query = db.query(Transaction)
    if db.bind.dialect.name == "postgresql":
        query = query.with_for_update()
    txn = query.filter(Transaction.id == transaction_id).first()

    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction with ID '{transaction_id}' not found")

    now = datetime.now(timezone.utc)

    # Idempotent return if already recovered
    if txn.status == "RECOVERED":
        return {
            "status": "RECOVERED",
            "transaction_id": txn.id,
            "recovered_amount": txn.amount,
            "verified": True,
            "message": "Payment was already verified and captured."
        }

    payment_id = req.payment_id if req else None
    signature = req.razorpay_signature if req else None

    # Check signature if provided
    if signature and txn.razorpay_order_id and payment_id:
        sig_valid = razorpay_service.verify_payment_signature(
            order_id=txn.razorpay_order_id,
            payment_id=payment_id,
            signature=signature
        )
        if not sig_valid:
            return {
                "status": "FAILED",
                "transaction_id": txn.id,
                "recovered_amount": 0.0,
                "verified": False,
                "message": "Invalid Razorpay payment signature."
            }

    # Fetch payments from Razorpay
    payments_to_check = []
    if payment_id:
        p_data = await razorpay_service.fetch_payment(payment_id)
        if p_data and p_data.get("id"):
            payments_to_check.append(p_data)
    elif txn.razorpay_order_id:
        order_payments = await razorpay_service.fetch_order_payments(txn.razorpay_order_id)
        payments_to_check.extend(order_payments)

    # Determine execution mode from recent recovery action or fallback
    last_act = db.query(RecoveryAction).filter(RecoveryAction.transaction_id == txn.id).order_by(RecoveryAction.created_at.desc()).first()
    mode = last_act.mode if last_act else "TEST_MODE"

    # Check for captured payment
    captured_pay = next((p for p in payments_to_check if p.get("status") == "captured"), None)
    if captured_pay:
        pay_id = captured_pay.get("id")
        txn.status = "RECOVERED"
        txn.razorpay_payment_id = pay_id
        txn.updated_at = now

        # Update or create recovery action
        if last_act and last_act.status != "SUCCESS":
            last_act.status = "SUCCESS"
            last_act.recovered_amount = txn.amount
            last_act.executed_at = now
        else:
            action_rec = RecoveryAction(
                id=f"act_{uuid.uuid4().hex[:12]}",
                transaction_id=txn.id,
                action_type="VERIFIED_PAYMENT",
                status="SUCCESS",
                ai_diagnosis="Payment independently verified via Razorpay API",
                ai_probability=1.0,
                ai_risk_level="LOW",
                ai_reasoning="Payment capture verified with gateway.",
                policy_allowed=True,
                policy_reasons_json="[]",
                requires_human_approval=False,
                recovered_amount=txn.amount,
                execution_details_json=json.dumps(captured_pay),
                mode=mode,
                created_at=now,
                executed_at=now
            )
            db.add(action_rec)

        # Audit Event
        audit_service.log_payment_recovered(
            db=db,
            transaction_id=txn.id,
            amount_recovered=txn.amount,
            payment_id=pay_id,
            mode=mode
        )
        db.commit()

        return {
            "status": "RECOVERED",
            "transaction_id": txn.id,
            "recovered_amount": txn.amount,
            "payment_id": pay_id,
            "verified": True,
            "message": f"Payment {pay_id} verified as captured. Revenue recovered: ₹{txn.amount:,.0f}"
        }

    # Check for failed payment
    failed_pay = next((p for p in payments_to_check if p.get("status") == "failed"), None)
    if failed_pay:
        txn.status = "FAILED"
        txn.updated_at = now

        if last_act and last_act.status != "SUCCESS":
            last_act.status = "FAILED"
            last_act.executed_at = now
        else:
            action_rec = RecoveryAction(
                id=f"act_{uuid.uuid4().hex[:12]}",
                transaction_id=txn.id,
                action_type="VERIFIED_PAYMENT",
                status="FAILED",
                ai_diagnosis="Payment failed on Razorpay gateway",
                ai_probability=0.0,
                ai_risk_level="HIGH",
                ai_reasoning=failed_pay.get("error_description", "Payment failed"),
                policy_allowed=True,
                policy_reasons_json="[]",
                requires_human_approval=False,
                recovered_amount=0.0,
                execution_details_json=json.dumps(failed_pay),
                mode=mode,
                created_at=now,
                executed_at=now
            )
            db.add(action_rec)

        audit_service.log_recovery_failed(
            db=db,
            transaction_id=txn.id,
            error_message=failed_pay.get("error_description", "Payment failed on gateway")
        )
        db.commit()

        return {
            "status": "FAILED",
            "transaction_id": txn.id,
            "recovered_amount": 0.0,
            "verified": False,
            "message": f"Payment failed on gateway: {failed_pay.get('error_description', 'Payment failed')}"
        }

    # Otherwise remains pending
    return {
        "status": txn.status,
        "transaction_id": txn.id,
        "recovered_amount": 0.0,
        "verified": False,
        "message": "Payment not yet captured on gateway. Status remains pending."
    }

@router.get("/audit", response_model=List[AuditEventSchema])
def list_audit_trail(
    transaction_id: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Retrieve immutable audit events for complete compliance & explainability."""
    query = db.query(AuditEvent)
    if transaction_id:
        query = query.filter(AuditEvent.transaction_id == transaction_id)
    if actor and actor != "ALL":
        query = query.filter(AuditEvent.actor == actor)

    events = query.order_by(desc(AuditEvent.timestamp)).limit(limit).all()
    return [AuditEventSchema(**e.to_dict()) for e in events]
