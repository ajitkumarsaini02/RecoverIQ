import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.db.models import Transaction
from app.services.ai_agent import AIAgentRecommendation

class PolicyRuleResult(BaseModel):
    rule_id: str
    description: str
    passed: bool
    reason: str

class PolicyEvaluationResult(BaseModel):
    allowed: bool = Field(description="Whether the action is allowed by policy rules")
    action: str = Field(description="Authorized action (may be modified/overridden to STOP or REMINDER)")
    requires_human_approval: bool = Field(description="Whether human merchant sign-off is mandatory")
    reason: str = Field(description="Primary human-readable reason summarizing the policy decision")
    reasons: List[str] = Field(default_factory=list, description="All evaluated rule rationales")
    rules_evaluated: List[PolicyRuleResult] = Field(default_factory=list, description="Detailed breakdown of each rule check")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "action": self.action,
            "requires_human_approval": self.requires_human_approval,
            "reason": self.reason,
            "reasons": self.reasons,
            "rules_evaluated": [r.model_dump() for r in self.rules_evaluated]
        }

class DeterministicPolicyEngine:
    """
    Strict, deterministic policy engine governing AI recommendations.
    AI recommends -> Policy engine decides whether that recommendation is allowed.
    Flow:
    AI Recommendation -> Policy Engine -> Allowed? (YES / NO) -> Execute / Human Approval
    """
    MAX_RETRIES = 2
    HIGH_VALUE_THRESHOLD = 20000.0 # INR
    LOW_PROBABILITY_THRESHOLD = 0.25 # 25% minimum floor
    COOLDOWN_SECONDS = 30 # seconds

    def evaluate(self, transaction: Transaction, recommendation: AIAgentRecommendation) -> PolicyEvaluationResult:
        rules_evaluated: List[PolicyRuleResult] = []
        reasons: List[str] = []
        action = recommendation.recommended_action
        requires_human_approval = recommendation.requires_human_approval
        allowed = True

        # Rule 1: Maximum 2 Automatic Retry Attempts (Ceiling)
        if action == "RETRY_PAYMENT" and (transaction.retry_count or 0) >= self.MAX_RETRIES:
            allowed = False
            action = "STOP"
            reason_msg = f"Exceeded maximum automated retry limit ({self.MAX_RETRIES} allowed, {transaction.retry_count} attempted). Action overridden to STOP."
            reasons.append(reason_msg)
            rules_evaluated.append(PolicyRuleResult(
                rule_id="RULE_MAX_RETRIES",
                description="Enforce ceiling of 2 automatic retries",
                passed=False,
                reason=reason_msg
            ))
        else:
            rules_evaluated.append(PolicyRuleResult(
                rule_id="RULE_MAX_RETRIES",
                description="Enforce ceiling of 2 automatic retries",
                passed=True,
                reason=f"Current retries ({transaction.retry_count or 0}) is within limit ({self.MAX_RETRIES})."
            ))

        # Rule 2: High-Value Transaction Gate (>= ₹20,000)
        if transaction.amount >= self.HIGH_VALUE_THRESHOLD:
            requires_human_approval = True
            reason_msg = f"Transaction amount ₹{transaction.amount:,.0f} exceeds high-value threshold (₹{self.HIGH_VALUE_THRESHOLD:,.0f}). Mandatory merchant approval required."
            reasons.append(reason_msg)
            rules_evaluated.append(PolicyRuleResult(
                rule_id="RULE_HIGH_VALUE_GATE",
                description="High-value payments require human approval",
                passed=False, # Triggered approval gate
                reason=reason_msg
            ))
        else:
            rules_evaluated.append(PolicyRuleResult(
                rule_id="RULE_HIGH_VALUE_GATE",
                description="High-value payments require human approval",
                passed=True,
                reason=f"Amount ₹{transaction.amount:,.0f} is within automated recovery limit."
            ))

        # Rule 3: Repeated Failures -> STOP Condition
        if (transaction.previous_failed_payments or 0) >= 3 and (transaction.retry_count or 0) >= 1:
            allowed = False
            action = "STOP"
            reason_msg = f"Customer has high repeat failure frequency ({transaction.previous_failed_payments} prior failures). Action converted to STOP."
            reasons.append(reason_msg)
            rules_evaluated.append(PolicyRuleResult(
                rule_id="RULE_REPEATED_FAILURES",
                description="Halt recovery on chronic repeat failure histories",
                passed=False,
                reason=reason_msg
            ))
        else:
            rules_evaluated.append(PolicyRuleResult(
                rule_id="RULE_REPEATED_FAILURES",
                description="Halt recovery on chronic repeat failure histories",
                passed=True,
                reason="Customer failure history is within safe thresholds."
            ))

        # Rule 4: Very Low Recovery Probability -> STOP
        if recommendation.recovery_probability < self.LOW_PROBABILITY_THRESHOLD:
            action = "STOP"
            allowed = False
            reason_msg = f"Recovery probability ({recommendation.recovery_probability:.1%}) is below minimum floor ({self.LOW_PROBABILITY_THRESHOLD:.1%}). Payment marked STOP."
            reasons.append(reason_msg)
            rules_evaluated.append(PolicyRuleResult(
                rule_id="RULE_MIN_PROBABILITY",
                description="Stop recovery when probability is below 25%",
                passed=False,
                reason=reason_msg
            ))
        else:
            rules_evaluated.append(PolicyRuleResult(
                rule_id="RULE_MIN_PROBABILITY",
                description="Stop recovery when probability is below 25%",
                passed=True,
                reason=f"Recovery probability ({recommendation.recovery_probability:.1%}) satisfies minimum threshold."
            ))

        # Rule 5: Cooldown Window for Immediate Retries
        if action == "RETRY_PAYMENT" and transaction.last_recovery_attempt_at:
            time_since_last = datetime.now(timezone.utc) - transaction.last_recovery_attempt_at.replace(tzinfo=timezone.utc)
            if time_since_last < timedelta(seconds=self.COOLDOWN_SECONDS):
                allowed = False
                action = "REMINDER"
                reason_msg = f"Retry attempted {int(time_since_last.total_seconds())}s ago (cooldown is {self.COOLDOWN_SECONDS}s). Converted to scheduled reminder."
                reasons.append(reason_msg)
                rules_evaluated.append(PolicyRuleResult(
                    rule_id="RULE_COOLDOWN_WINDOW",
                    description="Prevent rapid back-to-back retries without cooldown",
                    passed=False,
                    reason=reason_msg
                ))
            else:
                rules_evaluated.append(PolicyRuleResult(
                    rule_id="RULE_COOLDOWN_WINDOW",
                    description="Prevent rapid back-to-back retries without cooldown",
                    passed=True,
                    reason="Cooldown period satisfied."
                ))
        else:
            rules_evaluated.append(PolicyRuleResult(
                rule_id="RULE_COOLDOWN_WINDOW",
                description="Prevent rapid back-to-back retries without cooldown",
                passed=True,
                reason="No active cooldown violation."
            ))

        # Rule 6: Risky Actions / High Risk Level -> HUMAN APPROVAL
        if recommendation.risk_level == "HIGH" and action != "STOP":
            requires_human_approval = True
            reason_msg = "High risk assessment identified by AI engine. Gating for human operator review."
            reasons.append(reason_msg)
            rules_evaluated.append(PolicyRuleResult(
                rule_id="RULE_HIGH_RISK_GATE",
                description="High risk actions require human operator confirmation",
                passed=False,
                reason=reason_msg
            ))
        else:
            rules_evaluated.append(PolicyRuleResult(
                rule_id="RULE_HIGH_RISK_GATE",
                description="High risk actions require human operator confirmation",
                passed=True,
                reason="Risk level within automated policy tolerance."
            ))

        primary_reason = reasons[0] if reasons else "All deterministic safety guardrails passed successfully."

        return PolicyEvaluationResult(
            allowed=allowed,
            action=action,
            requires_human_approval=requires_human_approval,
            reason=primary_reason,
            reasons=reasons,
            rules_evaluated=rules_evaluated
        )

policy_engine = DeterministicPolicyEngine()
