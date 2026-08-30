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
async def execute_recovery_for_transaction(transaction_id: str, db: Session = Depends(get_db)):
    """
    Executes the 5-step recovery workflow:
    Failed Payment -> AI Analysis -> Policy Validation -> Recovery Action -> Result
    """
    txn = db.query(Transaction).options(joinedload(Transaction.customer)).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction with ID '{transaction_id}' not found.")

    result = await recovery_executor.execute_recovery(db=db, transaction=txn)
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
            "created_at": act.created_at.isoformat() if act.created_at else None
        })

    return results

@router.post("/recovery/approve/{action_id}")
def approve_action(action_id: str, db: Session = Depends(get_db)):
    """Approve a gated recovery action and execute it safely."""
    act = db.query(RecoveryAction).options(joinedload(RecoveryAction.transaction)).filter(RecoveryAction.id == action_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="Recovery action not found")

    if act.status != "PENDING_APPROVAL":
        return {"status": act.status, "message": f"Action is already in '{act.status}' status."}

    now = datetime.now(timezone.utc)
    act.status = "SUCCESS"
    act.approved_by = "Merchant Operator"
    act.approved_at = now
    act.executed_at = now
    act.recovered_amount = act.transaction.amount

    if act.transaction:
        act.transaction.status = "RECOVERED"
        act.transaction.retry_count += 1
        act.transaction.updated_at = now

    # Log APPROVED Audit Event
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

    aud_rec = AuditEvent(
        id=f"aud_{uuid.uuid4().hex[:12]}",
        timestamp=now + timedelta(milliseconds=100),
        transaction_id=act.transaction_id,
        event_type="PAYMENT_RECOVERED",
        actor="RAZORPAY_GATEWAY",
        decision="REVENUE_RECOVERED",
        details_json=json.dumps({"recovered_amount": act.recovered_amount, "mode": act.mode})
    )
    db.add(aud_rec)
    db.commit()

    return {
        "status": "APPROVED_AND_EXECUTED",
        "action_id": act.id,
        "recovered_amount": act.recovered_amount,
        "message": f"Approved and recovered ₹{act.recovered_amount:,.0f}"
    }

@router.post("/recovery/reject/{action_id}")
def reject_action(action_id: str, req: Optional[RejectRequest] = None, db: Session = Depends(get_db)):
    """Reject a gated recovery action and halt recovery."""
    act = db.query(RecoveryAction).options(joinedload(RecoveryAction.transaction)).filter(RecoveryAction.id == action_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="Recovery action not found")

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
