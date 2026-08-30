import json
import logging
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.config import settings
from app.db.models import Transaction, Customer

logger = logging.getLogger("recoveriq.ai_agent")

ActionType = Literal[
    "RETRY_PAYMENT", 
    "PAYMENT_LINK", 
    "ALTERNATIVE_PAYMENT_METHOD", 
    "REMINDER", 
    "HUMAN_ESCALATION", 
    "STOP"
]

RiskLevelType = Literal["LOW", "MEDIUM", "HIGH"]

class AIAnalysisInput(BaseModel):
    transaction_id: str
    amount: float
    currency: str = "INR"
    payment_method: str
    failure_reason: str
    error_code: Optional[str] = None
    retry_count: int = 0
    customer_id: str
    customer_name: str
    customer_email: str
    customer_lifetime_value: float
    previous_successful_payments: int
    previous_failed_payments: int
    previous_recovery_attempts: int

class AIAgentRecommendation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    diagnosis: str = Field(description="Failure diagnosis explaining the exact technical/behavioral cause")
    recovery_probability: float = Field(ge=0.0, le=1.0, description="Calibrated recovery probability between 0.0 and 1.0")
    recommended_action: ActionType = Field(description="Safe recovery action: RETRY_PAYMENT, PAYMENT_LINK, ALTERNATIVE_PAYMENT_METHOD, REMINDER, HUMAN_ESCALATION, STOP")
    risk_level: RiskLevelType = Field(description="Risk assessment: LOW, MEDIUM, HIGH")
    reason: str = Field(description="Explainable customer context reasoning grounding the decision")
    requires_human_approval: bool = Field(description="Whether merchant operator approval is recommended")
    mode: str = Field(default="DEMO_FALLBACK", description="LIVE_LLM or DEMO_FALLBACK")
    model_used: str = Field(default="DEMO / Rule-Based Expert Fallback", description="Identifier of the reasoning model")
    fallback_used: bool = Field(default=True, description="Whether DEMO fallback mode was engaged")

    @field_validator("recovery_probability")
    def validate_probability(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Recovery probability must be between 0.0 and 1.0, got {v}")
        return round(v, 2)

class RecoveryAIAgent:
    """
    AI Revenue Recovery Reasoning Agent.
    Analyzes failed payments against customer context and returns structured, Pydantic-validated JSON.
    Never executes payments directly (bounded AI paradigm).
    """

    def analyze_failure(
        self, 
        transaction: Transaction, 
        customer: Optional[Customer] = None
    ) -> AIAgentRecommendation:
        """
        Analyze the failed payment context and output structured recovery recommendation.
        """
        # Context gathering
        cust_name = "Valued Customer"
        cust_email = "customer@domain.in"
        cust_ltv = transaction.customer_lifetime_value or 0.0
        success_cnt = transaction.previous_successful_payments or 0
        failed_cnt = transaction.previous_failed_payments or 0
        retry_cnt = transaction.retry_count or 0

        if customer:
            cust_name = customer.name or cust_name
            cust_email = customer.email or cust_email
            cust_ltv = customer.lifetime_value
            success_cnt = customer.successful_payments_count
            failed_cnt = customer.failed_payments_count

        context = AIAnalysisInput(
            transaction_id=transaction.id,
            amount=transaction.amount,
            currency=transaction.currency or "INR",
            payment_method=transaction.payment_method,
            failure_reason=transaction.failure_reason,
            error_code=transaction.error_code,
            retry_count=retry_cnt,
            customer_id=transaction.customer_id,
            customer_name=cust_name,
            customer_email=cust_email,
            customer_lifetime_value=cust_ltv,
            previous_successful_payments=success_cnt,
            previous_failed_payments=failed_cnt,
            previous_recovery_attempts=transaction.previous_recovery_attempts or retry_cnt
        )

        # Check if live LLM credentials are configured
        if settings.is_ai_configured:
            try:
                live_result = self._call_llm_api(context)
                if live_result:
                    logger.info(f"Gemini AI reasoning successful for txn {context.transaction_id} using {live_result.model_used}")
                    return live_result
            except Exception as e:
                logger.warning(f"Live LLM API call failed ({type(e).__name__}): {e}. Gracefully activating heuristic fallback engine.")

        # Default / Graceful Fallback Heuristics Engine
        return self._run_expert_heuristics(context)

    def _call_llm_api(self, ctx: AIAnalysisInput) -> Optional[AIAgentRecommendation]:
        """
        Calls external LLM (Google Gemini or OpenAI) with structured JSON schema when API key is provided.
        """
        if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
            return self._call_gemini_api(ctx)
        elif settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
            return self._call_openai_api(ctx)
        return None

    def _call_gemini_api(self, ctx: AIAnalysisInput) -> Optional[AIAgentRecommendation]:
        """
        Executes real Google Gemini API call using REST endpoint with JSON schema output.
        """
        import httpx

        model = settings.GEMINI_MODEL or "gemini-1.5-flash"
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.GEMINI_API_KEY}"

        system_prompt = (
            "You are RecoverIQ, an expert fintech revenue recovery AI agent specialized in Indian payment systems (UPI, Card, Netbanking, Razorpay). "
            "Analyze the payment failure context and customer history. Output ONLY strict JSON adhering to the following schema:\n"
            "{\n"
            '  "diagnosis": "string (clear technical & behavioral root cause)",\n'
            '  "recovery_probability": float (0.0 to 1.0 calibrated probability of successful recovery),\n'
            '  "recommended_action": "RETRY_PAYMENT" | "PAYMENT_LINK" | "ALTERNATIVE_PAYMENT_METHOD" | "REMINDER" | "HUMAN_ESCALATION" | "STOP",\n'
            '  "risk_level": "LOW" | "MEDIUM" | "HIGH",\n'
            '  "reason": "string (explainable reasoning grounding the decision in customer LTV and transaction parameters)",\n'
            '  "requires_human_approval": boolean\n'
            "}\n"
            "Action guidelines:\n"
            "- RETRY_PAYMENT: For transient UPI/gateway timeouts with low risk and high LTV customers.\n"
            "- ALTERNATIVE_PAYMENT_METHOD: For bank issuer declines or payment method specific errors.\n"
            "- PAYMENT_LINK: For insufficient funds or high-value orders requiring white-glove links.\n"
            "- STOP: If retry limit reached (>=2) or customer has repeated chronic failures.\n"
            "- HUMAN_ESCALATION: For high-risk or enterprise transactions exceeding thresholds."
        )

        user_prompt = f"Failed Transaction & Customer Context:\n{ctx.model_dump_json(indent=2)}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"{system_prompt}\n\n{user_prompt}"
                        }
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(api_url, json=payload)
                if response.status_code != 200:
                    logger.error(f"Gemini API returned HTTP {response.status_code}: {response.text[:200]}")
                    return None

                res_data = response.json()
                candidates = res_data.get("candidates", [])
                if not candidates:
                    logger.warning("Gemini API returned no candidates.")
                    return None

                content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if not content_text:
                    return None

                parsed = json.loads(content_text)

                # Normalize action
                raw_action = str(parsed.get("recommended_action", "PAYMENT_LINK")).upper()
                if raw_action in ["STOP_RECOVERY", "HALT", "CANCEL"]:
                    raw_action = "STOP"
                elif raw_action in ["HUMAN_APPROVAL", "ESCALATE"]:
                    raw_action = "HUMAN_ESCALATION"
                elif raw_action not in ["RETRY_PAYMENT", "PAYMENT_LINK", "ALTERNATIVE_PAYMENT_METHOD", "REMINDER", "HUMAN_ESCALATION", "STOP"]:
                    raw_action = "PAYMENT_LINK"

                # Normalize risk
                raw_risk = str(parsed.get("risk_level", "LOW")).upper()
                if raw_risk not in ["LOW", "MEDIUM", "HIGH"]:
                    raw_risk = "MEDIUM"

                # Probability
                prob = float(parsed.get("recovery_probability", 0.5))
                prob = max(0.0, min(1.0, prob))

                return AIAgentRecommendation(
                    diagnosis=str(parsed.get("diagnosis", "Automated AI failure diagnosis")),
                    recovery_probability=round(prob, 2),
                    recommended_action=raw_action,
                    risk_level=raw_risk,
                    reason=str(parsed.get("reason", "AI assessed customer payment parameters.")),
                    requires_human_approval=bool(parsed.get("requires_human_approval", False) or ctx.amount >= 20000.0),
                    mode="GEMINI",
                    model_used=f"Google Gemini ({model})",
                    fallback_used=False
                )
        except Exception as e:
            logger.warning(f"Gemini API execution error ({type(e).__name__}): {e}")
            return None

    def _call_openai_api(self, ctx: AIAnalysisInput) -> Optional[AIAgentRecommendation]:
        """
        Executes OpenAI Chat Completion call with JSON output when configured.
        """
        import httpx

        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        system_prompt = (
            "You are RecoverIQ, an expert fintech revenue recovery AI agent. "
            "Analyze the payment failure and output strictly formatted JSON with: "
            "diagnosis, recovery_probability (0.0-1.0), recommended_action (RETRY_PAYMENT, PAYMENT_LINK, "
            "ALTERNATIVE_PAYMENT_METHOD, REMINDER, HUMAN_ESCALATION, STOP), risk_level (LOW, MEDIUM, HIGH), "
            "reason, requires_human_approval (boolean)."
        )

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context: {ctx.model_dump_json()}"}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                if response.status_code != 200:
                    logger.error(f"OpenAI API returned HTTP {response.status_code}: {response.text[:200]}")
                    return None

                res_json = response.json()
                content_str = res_json["choices"][0]["message"]["content"]
                parsed = json.loads(content_str)

                prob = max(0.0, min(1.0, float(parsed.get("recovery_probability", 0.5))))
                raw_action = str(parsed.get("recommended_action", "PAYMENT_LINK")).upper()
                if raw_action not in ["RETRY_PAYMENT", "PAYMENT_LINK", "ALTERNATIVE_PAYMENT_METHOD", "REMINDER", "HUMAN_ESCALATION", "STOP"]:
                    raw_action = "PAYMENT_LINK"

                return AIAgentRecommendation(
                    diagnosis=str(parsed.get("diagnosis", "AI failure diagnosis")),
                    recovery_probability=round(prob, 2),
                    recommended_action=raw_action,
                    risk_level=str(parsed.get("risk_level", "LOW")).upper() if str(parsed.get("risk_level", "LOW")).upper() in ["LOW", "MEDIUM", "HIGH"] else "MEDIUM",
                    reason=str(parsed.get("reason", "OpenAI assessed transaction parameters.")),
                    requires_human_approval=bool(parsed.get("requires_human_approval", False) or ctx.amount >= 20000.0),
                    mode="OPENAI",
                    model_used="OpenAI (gpt-4o-mini)",
                    fallback_used=False
                )
        except Exception as e:
            logger.warning(f"OpenAI API execution error: {e}")
            return None

    def _run_expert_heuristics(self, ctx: AIAnalysisInput) -> AIAgentRecommendation:
        """
        Domain-expert heuristic reasoning engine providing instant, explainable, and deterministic decisions.
        Clearly labeled as DEMO / RULE-BASED FALLBACK.
        """
        # Heuristic Rule 1: Exceeded 2 automated retries -> STOP
        if ctx.retry_count >= 2:
            return AIAgentRecommendation(
                diagnosis=f"Exceeded maximum automated retry limit ({ctx.retry_count} retries attempted).",
                recovery_probability=0.15,
                recommended_action="STOP",
                risk_level="HIGH",
                reason=f"Customer {ctx.customer_name} has experienced repeated failures. Additional automated retries pose card block or decline charge risks. Bounded by policy.",
                requires_human_approval=False,
                mode="DEMO_FALLBACK",
                model_used="RecoverIQ Expert Heuristics Engine",
                fallback_used=True
            )

        # Heuristic Rule 2: High Value Transaction (>= ₹20,000)
        if ctx.amount >= 20000.0:
            if ctx.failure_reason in ["UPI_TIMEOUT", "NETWORK_ERROR"]:
                prob = 0.88 if ctx.previous_successful_payments >= 2 else 0.72
                return AIAgentRecommendation(
                    diagnosis=f"High-value B2B/enterprise payment (₹{ctx.amount:,.0f}) halted due to {ctx.failure_reason.replace('_', ' ')}.",
                    recovery_probability=prob,
                    recommended_action="PAYMENT_LINK",
                    risk_level="MEDIUM",
                    reason=f"High transaction value (₹{ctx.amount:,.0f}) with customer {ctx.customer_name} (LTV: ₹{ctx.customer_lifetime_value:,.0f}). Sending a secure Razorpay Payment Link allows white-glove recovery.",
                    requires_human_approval=True,
                    mode="DEMO_FALLBACK",
                    model_used="RecoverIQ Expert Heuristics Engine",
                    fallback_used=True
                )
            elif ctx.failure_reason in ["INSUFFICIENT_FUNDS", "BANK_DECLINED"]:
                return AIAgentRecommendation(
                    diagnosis=f"High-value payment (₹{ctx.amount:,.0f}) declined by issuing bank.",
                    recovery_probability=0.45,
                    recommended_action="HUMAN_ESCALATION",
                    risk_level="HIGH",
                    reason=f"Large payment (₹{ctx.amount:,.0f}) declined by bank. Customer has {ctx.previous_failed_payments} past declines. Account manager escalation advised.",
                    requires_human_approval=True,
                    mode="DEMO_FALLBACK",
                    model_used="RecoverIQ Expert Heuristics Engine",
                    fallback_used=True
                )

        # Heuristic Rule 3: Temporary UPI Timeout
        if ctx.failure_reason == "UPI_TIMEOUT":
            prob = 0.91 if (ctx.previous_successful_payments >= 1 or ctx.customer_lifetime_value > 0) else 0.82
            return AIAgentRecommendation(
                diagnosis="Temporary UPI PSP timeout or NPCI network latency",
                recovery_probability=prob,
                recommended_action="RETRY_PAYMENT",
                risk_level="LOW",
                reason=f"Customer {ctx.customer_name} has strong historical reliability ({ctx.previous_successful_payments} successful payments, ₹{ctx.customer_lifetime_value:,.0f} LTV). Transient timeout has 91% recovery rate on safe retry.",
                requires_human_approval=False,
                mode="DEMO_FALLBACK",
                model_used="RecoverIQ Expert Heuristics Engine",
                fallback_used=True
            )

        # Heuristic Rule 4: Network Error
        if ctx.failure_reason == "NETWORK_ERROR":
            return AIAgentRecommendation(
                diagnosis="Transient network connection drop during gateway handshake",
                recovery_probability=0.88,
                recommended_action="RETRY_PAYMENT",
                risk_level="LOW",
                reason="Temporary network socket timeout during transaction authorization. Automatic retry after backoff is safe and highly effective.",
                requires_human_approval=False,
                mode="DEMO_FALLBACK",
                model_used="RecoverIQ Expert Heuristics Engine",
                fallback_used=True
            )

        # Heuristic Rule 5: Bank Issuer Decline
        if ctx.failure_reason == "BANK_DECLINED":
            return AIAgentRecommendation(
                diagnosis="Bank issuer decline or card restriction",
                recovery_probability=0.68,
                recommended_action="ALTERNATIVE_PAYMENT_METHOD",
                risk_level="MEDIUM",
                reason=f"Issuing bank declined the transaction. Prompting customer {ctx.customer_name} to switch to an alternative UPI or Netbanking method maximizes conversion.",
                requires_human_approval=False,
                mode="DEMO_FALLBACK",
                model_used="RecoverIQ Expert Heuristics Engine",
                fallback_used=True
            )

        # Heuristic Rule 6: Insufficient Funds
        if ctx.failure_reason == "INSUFFICIENT_FUNDS":
            return AIAgentRecommendation(
                diagnosis="Insufficient account balance or daily UPI spending limit reached",
                recovery_probability=0.55,
                recommended_action="PAYMENT_LINK",
                risk_level="MEDIUM",
                reason="Customer account lacked sufficient balance at checkout time. Sending a scheduled payment link allows completion after account reload.",
                requires_human_approval=False,
                mode="DEMO_FALLBACK",
                model_used="RecoverIQ Expert Heuristics Engine",
                fallback_used=True
            )

        # Heuristic Rule 7: Payment Method Error
        if ctx.failure_reason == "PAYMENT_METHOD_ERROR":
            return AIAgentRecommendation(
                diagnosis="Invalid payment credentials or expired token",
                recovery_probability=0.62,
                recommended_action="ALTERNATIVE_PAYMENT_METHOD",
                risk_level="LOW",
                reason="The payment method credentials entered were invalid or expired. Prompting customer for alternate method.",
                requires_human_approval=False,
                mode="DEMO_FALLBACK",
                model_used="RecoverIQ Expert Heuristics Engine",
                fallback_used=True
            )

        # Default fallback
        return AIAgentRecommendation(
            diagnosis="Unclassified payment gateway failure",
            recovery_probability=0.50,
            recommended_action="PAYMENT_LINK",
            risk_level="MEDIUM",
            reason="Unclassified payment failure. Standard safe payment link fallback recommended.",
            requires_human_approval=False,
            mode="DEMO_FALLBACK",
            model_used="RecoverIQ Expert Heuristics Engine",
            fallback_used=True
        )

ai_agent = RecoveryAIAgent()
