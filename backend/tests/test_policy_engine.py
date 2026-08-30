import pytest
from datetime import datetime, timezone, timedelta
from app.services.policy_engine import policy_engine, PolicyEvaluationResult
from app.services.ai_agent import AIAgentRecommendation
from app.db.models import Transaction, Customer

def test_policy_safe_approval_pass():
    """Standard transaction within limits should pass without human approval."""
    txn = Transaction(
        id="txn_safe_1",
        customer_id="cust_safe_1",
        amount=4999.0,
        currency="INR",
        status="FAILED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=0,
        max_retries=2
    )
    rec = AIAgentRecommendation(
        diagnosis="Temporary UPI timeout",
        recovery_probability=0.91,
        recommended_action="RETRY_PAYMENT",
        risk_level="LOW",
        reason="Clean customer history",
        requires_human_approval=False
    )
    result = policy_engine.evaluate(transaction=txn, recommendation=rec)
    assert result.allowed is True
    assert result.action == "RETRY_PAYMENT"
    assert result.requires_human_approval is False
    assert "within limit" in result.reason or "passed" in result.reason.lower()

def test_policy_retry_limit():
    """Rule 1: Exceeding 2 automated retries must override action to STOP."""
    txn = Transaction(
        id="txn_retry_limit",
        customer_id="cust_1",
        amount=4999.0,
        status="FAILED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=2, # Ceiling reached
        max_retries=2
    )
    rec = AIAgentRecommendation(
        diagnosis="Temporary UPI timeout",
        recovery_probability=0.85,
        recommended_action="RETRY_PAYMENT",
        risk_level="LOW",
        reason="AI wants to retry",
        requires_human_approval=False
    )
    result = policy_engine.evaluate(transaction=txn, recommendation=rec)
    assert result.allowed is False
    assert result.action == "STOP"
    assert "Exceeded maximum automated retry limit" in result.reason

def test_policy_high_value_transaction():
    """Rule 2: Transactions >= ₹20,000 must require human approval."""
    txn = Transaction(
        id="txn_high_val",
        customer_id="cust_2",
        amount=49999.0, # High value
        currency="INR",
        status="FAILED",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        retry_count=0
    )
    rec = AIAgentRecommendation(
        diagnosis="Bank decline",
        recovery_probability=0.75,
        recommended_action="PAYMENT_LINK",
        risk_level="MEDIUM",
        reason="High-value client",
        requires_human_approval=False # AI did not flag, but Policy Engine MUST enforce
    )
    result = policy_engine.evaluate(transaction=txn, recommendation=rec)
    assert result.requires_human_approval is True
    assert "exceeds high-value threshold" in result.reason

def test_policy_repeated_failures():
    """Rule 3: Repeated failures history must trigger STOP."""
    txn = Transaction(
        id="txn_repeat_fail",
        customer_id="cust_3",
        amount=2499.0,
        currency="INR",
        status="FAILED",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        previous_failed_payments=4, # Chronic declines
        retry_count=1
    )
    rec = AIAgentRecommendation(
        diagnosis="Bank decline",
        recovery_probability=0.60,
        recommended_action="ALTERNATIVE_PAYMENT_METHOD",
        risk_level="MEDIUM",
        reason="Retry alternate card",
        requires_human_approval=False
    )
    result = policy_engine.evaluate(transaction=txn, recommendation=rec)
    assert result.allowed is False
    assert result.action == "STOP"
    assert "repeat failure" in result.reason.lower()

def test_policy_low_recovery_probability():
    """Rule 4: Recovery probability below 25% must force STOP."""
    txn = Transaction(
        id="txn_low_prob",
        customer_id="cust_4",
        amount=999.0,
        status="FAILED",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        retry_count=0
    )
    rec = AIAgentRecommendation(
        diagnosis="Stolen card decline",
        recovery_probability=0.10, # Very low
        recommended_action="RETRY_PAYMENT",
        risk_level="HIGH",
        reason="Low confidence",
        requires_human_approval=False
    )
    result = policy_engine.evaluate(transaction=txn, recommendation=rec)
    assert result.allowed is False
    assert result.action == "STOP"
    assert "below minimum floor" in result.reason or "below safety threshold" in result.reason

def test_policy_cooldown_window():
    """Rule 5: Retrying within 30-second cooldown window converts to scheduled REMINDER."""
    txn = Transaction(
        id="txn_cooldown",
        customer_id="cust_5",
        amount=1499.0,
        status="FAILED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=1,
        last_recovery_attempt_at=datetime.now(timezone.utc) - timedelta(seconds=10) # 10s ago (< 30s)
    )
    rec = AIAgentRecommendation(
        diagnosis="UPI Timeout",
        recovery_probability=0.90,
        recommended_action="RETRY_PAYMENT",
        risk_level="LOW",
        reason="Try again",
        requires_human_approval=False
    )
    result = policy_engine.evaluate(transaction=txn, recommendation=rec)
    assert result.allowed is False
    assert result.action == "REMINDER"
    assert "cooldown" in result.reason.lower()

def test_policy_high_risk_human_approval():
    """Rule 6: High-risk level must mandate human operator verification."""
    txn = Transaction(
        id="txn_high_risk",
        customer_id="cust_6",
        amount=9999.0,
        status="FAILED",
        payment_method="CARD",
        failure_reason="PAYMENT_METHOD_ERROR",
        retry_count=0
    )
    rec = AIAgentRecommendation(
        diagnosis="Fraud suspicion flag",
        recovery_probability=0.50,
        recommended_action="PAYMENT_LINK",
        risk_level="HIGH", # High risk
        reason="Requires merchant verification",
        requires_human_approval=False
    )
    result = policy_engine.evaluate(transaction=txn, recommendation=rec)
    assert result.requires_human_approval is True
    assert "High risk assessment" in result.reason

def test_policy_invalid_action_name_failsafe_stop():
    """Invalid or corrupted recommendation action is rejected by Pydantic and safely handled by Policy Engine."""
    from pydantic import ValidationError

    # 1. Pydantic schema rejects invalid action literals
    with pytest.raises(ValidationError):
        AIAgentRecommendation(
            diagnosis="Corrupted action test",
            recovery_probability=0.80,
            recommended_action="UNKNOWN_UNSAFE_ACTION",
            risk_level="LOW",
            reason="Invalid action payload",
            requires_human_approval=False
        )

    # 2. Policy engine overrides any corrupted action to STOP
    txn = Transaction(
        id="txn_invalid_act",
        customer_id="cust_inv",
        amount=1999.0,
        status="FAILED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=0
    )
    rec = AIAgentRecommendation(
        diagnosis="Valid diagnosis",
        recovery_probability=0.80,
        recommended_action="PAYMENT_LINK",
        risk_level="LOW",
        reason="Valid reasoning",
        requires_human_approval=False
    )
    # Simulate runtime property modification
    object.__setattr__(rec, "recommended_action", "FORGED_ACTION")
    result = policy_engine.evaluate(transaction=txn, recommendation=rec)
    assert result.allowed is False
    assert result.action == "STOP"
    assert "Invalid or unrecognized" in result.reason

def test_policy_combination_high_value_and_retry_limit():
    """When both High Value and Max Retries apply, Retry ceiling takes precedence and forces STOP."""
    txn = Transaction(
        id="txn_hv_retry_cap",
        customer_id="cust_comb_1",
        amount=50000.0, # High value
        status="FAILED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=2 # Max retry reached
    )
    rec = AIAgentRecommendation(
        diagnosis="Retry attempt on high-value txn",
        recovery_probability=0.85,
        recommended_action="RETRY_PAYMENT",
        risk_level="LOW",
        reason="AI asks to retry",
        requires_human_approval=False
    )
    result = policy_engine.evaluate(transaction=txn, recommendation=rec)
    assert result.allowed is False
    assert result.action == "STOP"
    assert result.requires_human_approval is True # Flagged for high-value audit

def test_policy_combination_low_prob_and_high_risk():
    """When both Low Probability and High Risk apply, action is STOP."""
    txn = Transaction(
        id="txn_low_prob_high_risk",
        customer_id="cust_comb_2",
        amount=5000.0,
        status="FAILED",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        retry_count=0
    )
    rec = AIAgentRecommendation(
        diagnosis="High risk with low recovery likelihood",
        recovery_probability=0.12, # < 0.25
        recommended_action="PAYMENT_LINK",
        risk_level="HIGH",
        reason="High risk fraud detection",
        requires_human_approval=False
    )
    result = policy_engine.evaluate(transaction=txn, recommendation=rec)
    assert result.allowed is False
    assert result.action == "STOP"
