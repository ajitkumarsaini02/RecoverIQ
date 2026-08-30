import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.db.models import AuditEvent

class AuditService:
    """
    Dedicated Audit Trail Service.
    Guarantees every money-related action and decision is permanently logged.
    """

    @staticmethod
    def log_event(
        db: Session,
        event_type: str,
        actor: str,
        transaction_id: Optional[str] = None,
        decision: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        commit: bool = True
    ) -> AuditEvent:
        """
        Records an immutable audit event in the database.
        """
        now = datetime.now(timezone.utc)
        payload = details or {}

        event = AuditEvent(
            id=f"aud_{uuid.uuid4().hex[:12]}",
            timestamp=now,
            transaction_id=transaction_id,
            event_type=event_type,
            actor=actor,
            decision=decision,
            details_json=json.dumps(payload)
        )
        db.add(event)
        if commit:
            db.commit()
            db.refresh(event)
        return event

    @staticmethod
    def log_payment_failed(db: Session, transaction_id: str, amount: float, failure_reason: str, error_code: Optional[str] = None, mode: str = "TEST_MODE"):
        return AuditService.log_event(
            db=db,
            event_type="PAYMENT_FAILED",
            actor="RAZORPAY_GATEWAY",
            transaction_id=transaction_id,
            decision="FAILURE_RECORDED",
            details={"amount": amount, "currency": "INR", "failure_reason": failure_reason, "error_code": error_code, "mode": mode}
        )

    @staticmethod
    def log_failure_analyzed(db: Session, transaction_id: str, diagnosis: str, failure_reason: str):
        return AuditService.log_event(
            db=db,
            event_type="FAILURE_ANALYZED",
            actor="AI_AGENT",
            transaction_id=transaction_id,
            decision="DIAGNOSIS_COMPLETE",
            details={"diagnosis": diagnosis, "failure_reason": failure_reason}
        )

    @staticmethod
    def log_customer_context_analyzed(db: Session, transaction_id: str, customer_id: str, customer_ltv: float, successful_payments: int, failed_payments: int):
        return AuditService.log_event(
            db=db,
            event_type="CUSTOMER_CONTEXT_ANALYZED",
            actor="AI_AGENT",
            transaction_id=transaction_id,
            decision="CONTEXT_EVALUATED",
            details={"customer_id": customer_id, "customer_ltv": customer_ltv, "successful_payments": successful_payments, "failed_payments": failed_payments}
        )

    @staticmethod
    def log_ai_recommendation(db: Session, transaction_id: str, action: str, probability: float, risk_level: str, reason: str):
        return AuditService.log_event(
            db=db,
            event_type="AI_RECOMMENDATION",
            actor="AI_AGENT",
            transaction_id=transaction_id,
            decision=action,
            details={"recommended_action": action, "recovery_probability": probability, "risk_level": risk_level, "reason": reason}
        )

    @staticmethod
    def log_policy_validated(db: Session, transaction_id: str, allowed: bool, action: str, requires_human_approval: bool, reason: str):
        return AuditService.log_event(
            db=db,
            event_type="POLICY_VALIDATED",
            actor="POLICY_ENGINE",
            transaction_id=transaction_id,
            decision="APPROVED" if (allowed and not requires_human_approval) else ("APPROVAL_REQUIRED" if requires_human_approval else "STOP"),
            details={"allowed": allowed, "action": action, "requires_human_approval": requires_human_approval, "reason": reason}
        )

    @staticmethod
    def log_approval_requested(db: Session, transaction_id: str, action_id: str, amount: float, reason: str):
        return AuditService.log_event(
            db=db,
            event_type="APPROVAL_REQUESTED",
            actor="POLICY_ENGINE",
            transaction_id=transaction_id,
            decision="GATED_FOR_APPROVAL",
            details={"action_id": action_id, "amount": amount, "reason": reason}
        )

    @staticmethod
    def log_action_approved(db: Session, transaction_id: str, action_id: str, actor: str = "HUMAN_OPERATOR"):
        return AuditService.log_event(
            db=db,
            event_type="ACTION_APPROVED",
            actor=actor,
            transaction_id=transaction_id,
            decision="ACTION_APPROVED",
            details={"action_id": action_id, "status": "APPROVED"}
        )

    @staticmethod
    def log_action_rejected(db: Session, transaction_id: str, action_id: str, reason: str, actor: str = "HUMAN_OPERATOR"):
        return AuditService.log_event(
            db=db,
            event_type="ACTION_REJECTED",
            actor=actor,
            transaction_id=transaction_id,
            decision="ACTION_REJECTED",
            details={"action_id": action_id, "rejection_reason": reason}
        )

    @staticmethod
    def log_recovery_executed(db: Session, transaction_id: str, action: str, mode: str):
        return AuditService.log_event(
            db=db,
            event_type="RECOVERY_EXECUTED",
            actor="RAZORPAY_GATEWAY",
            transaction_id=transaction_id,
            decision="RECOVERY_DISPATCHED",
            details={"action": action, "mode": mode}
        )

    @staticmethod
    def log_recovery_succeeded(db: Session, transaction_id: str, amount_recovered: float, mode: str):
        return AuditService.log_event(
            db=db,
            event_type="RECOVERY_SUCCEEDED",
            actor="RAZORPAY_GATEWAY",
            transaction_id=transaction_id,
            decision="REVENUE_RECOVERED",
            details={"amount_recovered": amount_recovered, "mode": mode}
        )

    @staticmethod
    def log_recovery_failed(db: Session, transaction_id: str, error_message: str):
        return AuditService.log_event(
            db=db,
            event_type="RECOVERY_FAILED",
            actor="RAZORPAY_GATEWAY",
            transaction_id=transaction_id,
            decision="RECOVERY_FAILED",
            details={"error": error_message}
        )

    @staticmethod
    def log_recovery_stopped(db: Session, transaction_id: str, reason: str):
        return AuditService.log_event(
            db=db,
            event_type="RECOVERY_STOPPED",
            actor="POLICY_ENGINE",
            transaction_id=transaction_id,
            decision="STOP_ENFORCED",
            details={"reason": reason}
        )

audit_service = AuditService()
