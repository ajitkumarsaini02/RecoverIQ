from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class CustomerSchema(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    lifetime_value: float
    successful_payments_count: int
    failed_payments_count: int
    risk_score: float
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class RecoveryActionSchema(BaseModel):
    id: str
    transaction_id: str
    action_type: str
    status: str
    ai_diagnosis: str
    ai_probability: float
    ai_risk_level: str
    ai_reasoning: str
    policy_allowed: bool
    policy_reasons: List[str] = Field(default_factory=list)
    requires_human_approval: bool
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    recovered_amount: float = 0.0
    execution_details: Dict[str, Any] = Field(default_factory=dict)
    mode: str
    created_at: Optional[str] = None
    executed_at: Optional[str] = None

class AuditEventSchema(BaseModel):
    id: str
    timestamp: Optional[str] = None
    transaction_id: Optional[str] = None
    event_type: str
    actor: str
    decision: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

class TransactionSchema(BaseModel):
    id: str
    customer_id: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    amount: float
    currency: str = "INR"
    status: str
    payment_method: str
    failure_reason: str
    error_code: Optional[str] = None
    customer_lifetime_value: float = 0.0
    previous_successful_payments: int = 0
    previous_failed_payments: int = 0
    previous_recovery_attempts: int = 0
    retry_count: int = 0
    max_retries: int = 2
    last_recovery_attempt_at: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_payment_link: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    customer: Optional[CustomerSchema] = None
    recovery_actions: Optional[List[RecoveryActionSchema]] = None
    audit_events: Optional[List[AuditEventSchema]] = None

class TransactionListResponse(BaseModel):
    items: List[TransactionSchema]
    total: int
    page: int
    page_size: int
    total_pages: int
    data_label: str = "DEMO / SYNTHETIC DATA"
