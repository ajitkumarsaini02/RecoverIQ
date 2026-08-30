import json
from datetime import datetime, timezone
from sqlalchemy import (
    Column, 
    String, 
    Float, 
    Integer, 
    Boolean, 
    DateTime, 
    ForeignKey, 
    Text, 
    Index
)
from sqlalchemy.orm import relationship
from app.db.session import Base

def utcnow():
    return datetime.now(timezone.utc)

class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(64), primary_key=True, index=True) # e.g. cust_001
    name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=False, index=True)
    phone = Column(String(32), nullable=False)
    lifetime_value = Column(Float, default=0.0, nullable=False)
    successful_payments_count = Column(Integer, default=0, nullable=False)
    failed_payments_count = Column(Integer, default=0, nullable=False)
    risk_score = Column(Float, default=0.1, nullable=False) # 0.0 to 1.0
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    transactions = relationship("Transaction", back_populates="customer", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "lifetime_value": self.lifetime_value,
            "successful_payments_count": self.successful_payments_count,
            "failed_payments_count": self.failed_payments_count,
            "risk_score": self.risk_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(64), primary_key=True, index=True) # e.g. txn_001
    customer_id = Column(String(64), ForeignKey("customers.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="INR", nullable=False)
    status = Column(String(32), default="FAILED", nullable=False, index=True)
    payment_method = Column(String(32), nullable=False, index=True) # UPI, CARD, NETBANKING, WALLET
    failure_reason = Column(String(64), nullable=False, index=True) # UPI_TIMEOUT, BANK_DECLINED, etc.
    error_code = Column(String(64), nullable=True)
    
    # Customer Context snapshot for explainable AI reasoning
    customer_lifetime_value = Column(Float, default=0.0, nullable=False)
    previous_successful_payments = Column(Integer, default=0, nullable=False)
    previous_failed_payments = Column(Integer, default=0, nullable=False)
    previous_recovery_attempts = Column(Integer, default=0, nullable=False)
    
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=2, nullable=False)
    last_recovery_attempt_at = Column(DateTime, nullable=True)
    
    # Razorpay Test Mode reference attributes
    razorpay_order_id = Column(String(64), nullable=True)
    razorpay_payment_id = Column(String(64), nullable=True)
    razorpay_payment_link = Column(String(256), nullable=True)
    
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    customer = relationship("Customer", back_populates="transactions")
    recovery_actions = relationship("RecoveryAction", back_populates="transaction", cascade="all, delete-orphan", order_by="desc(RecoveryAction.created_at)")
    audit_events = relationship("AuditEvent", back_populates="transaction", cascade="all, delete-orphan", order_by="desc(AuditEvent.timestamp)")

    __table_args__ = (
        Index("idx_txn_status_reason", "status", "failure_reason"),
        Index("idx_txn_created_amount", "created_at", "amount"),
    )

    def to_dict(self, include_relations=True):
        data = {
            "id": self.id,
            "customer_id": self.customer_id,
            "customer_name": self.customer.name if self.customer else None,
            "customer_email": self.customer.email if self.customer else None,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "payment_method": self.payment_method,
            "failure_reason": self.failure_reason,
            "error_code": self.error_code,
            "customer_lifetime_value": self.customer_lifetime_value,
            "previous_successful_payments": self.previous_successful_payments,
            "previous_failed_payments": self.previous_failed_payments,
            "previous_recovery_attempts": self.previous_recovery_attempts,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "last_recovery_attempt_at": self.last_recovery_attempt_at.isoformat() if self.last_recovery_attempt_at else None,
            "razorpay_order_id": self.razorpay_order_id,
            "razorpay_payment_id": self.razorpay_payment_id,
            "razorpay_payment_link": self.razorpay_payment_link,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_relations and self.customer:
            data["customer"] = self.customer.to_dict()
        return data

class RecoveryAction(Base):
    __tablename__ = "recovery_actions"

    id = Column(String(64), primary_key=True, index=True) # e.g. act_001
    transaction_id = Column(String(64), ForeignKey("transactions.id"), nullable=False, index=True)
    action_type = Column(String(64), nullable=False) # RETRY_PAYMENT, PAYMENT_LINK, etc.
    status = Column(String(32), default="PENDING_APPROVAL", nullable=False, index=True) # PENDING_APPROVAL, APPROVED, REJECTED, SUCCESS, FAILED
    
    # AI Reasoning
    ai_diagnosis = Column(String(256), nullable=False)
    ai_probability = Column(Float, nullable=False)
    ai_risk_level = Column(String(16), nullable=False) # LOW, MEDIUM, HIGH
    ai_reasoning = Column(Text, nullable=False)
    
    # Policy Guardrail validation
    policy_allowed = Column(Boolean, default=False, nullable=False)
    policy_reasons_json = Column(Text, default="[]", nullable=False)
    requires_human_approval = Column(Boolean, default=False, nullable=False)
    
    # Approval metadata
    approved_by = Column(String(64), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String(256), nullable=True)
    
    # Outcome
    recovered_amount = Column(Float, default=0.0, nullable=False)
    execution_details_json = Column(Text, default="{}", nullable=False)
    mode = Column(String(32), default="TEST_MODE", nullable=False) # TEST_MODE or SIMULATION_MODE
    
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    executed_at = Column(DateTime, nullable=True)

    transaction = relationship("Transaction", back_populates="recovery_actions")

    def to_dict(self):
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "action_type": self.action_type,
            "status": self.status,
            "ai_diagnosis": self.ai_diagnosis,
            "ai_probability": self.ai_probability,
            "ai_risk_level": self.ai_risk_level,
            "ai_reasoning": self.ai_reasoning,
            "policy_allowed": self.policy_allowed,
            "policy_reasons": json.loads(self.policy_reasons_json) if self.policy_reasons_json else [],
            "requires_human_approval": self.requires_human_approval,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "recovered_amount": self.recovered_amount,
            "execution_details": json.loads(self.execution_details_json) if self.execution_details_json else {},
            "mode": self.mode,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(64), primary_key=True, index=True) # e.g. aud_001
    timestamp = Column(DateTime, default=utcnow, nullable=False, index=True)
    transaction_id = Column(String(64), ForeignKey("transactions.id"), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    actor = Column(String(32), nullable=False, index=True) # SYSTEM, AI_AGENT, POLICY_ENGINE, HUMAN_OPERATOR, RAZORPAY_GATEWAY
    decision = Column(String(64), nullable=True)
    details_json = Column(Text, default="{}", nullable=False)

    transaction = relationship("Transaction", back_populates="audit_events")

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "transaction_id": self.transaction_id,
            "event_type": self.event_type,
            "actor": self.actor,
            "decision": self.decision,
            "details": json.loads(self.details_json) if self.details_json else {},
        }
