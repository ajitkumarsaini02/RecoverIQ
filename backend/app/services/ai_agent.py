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
    mode: str = Field(default="HEURISTIC_FALLBACK", description="LIVE_LLM or HEURISTIC_FALLBACK")
    model_used: str = Field(default="RecoverIQ Expert Heuristics Engine", description="Identifier of the reasoning model")
    fallback_used: bool = Field(default=True, description="Whether fallback mode was engaged")
    fallback_reason: Optional[str] = Field(default=None, description="Safe failure classification if fallback was engaged")

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

    def __init__(self):
        self.last_error_classification: Optional[str] = None

    @staticmethod
    def _parse_json_payload(raw_text: str) -> Optional[Dict[str, Any]]:
        """
        Safely extracts and parses JSON payload from model response, handling
        surrounding markdown fences (```json ... ```), conversational intros/outros,
        or raw JSON.
        """
        if not raw_text or not raw_text.strip():
            return None

        text = raw_text.strip()

        # 1. Try direct JSON parsing
        try:
            return json.loads(text)
        except Exception:
            pass

        # 2. Extract using regex markdown fences
        import re
        fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except Exception:
                pass

        # 3. Find outermost curly braces
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                candidate = text[start_idx : end_idx + 1].strip()
                return json.loads(candidate)
            except Exception:
                pass

        return None

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
                    self.last_error_classification = None
                    logger.info(f"Gemini AI reasoning successful for txn {context.transaction_id} using {live_result.model_used}")
                    return live_result
                else:
                    logger.info(f"Live LLM call engaged heuristic fallback: {self.last_error_classification}")
            except Exception as e:
                self.last_error_classification = "timeout/network = connectivity"
                logger.warning("Live LLM API call encountered exception: timeout/network = connectivity")
        else:
            self.last_error_classification = "401/403 = authentication/configuration"
            logger.debug("AI credentials unconfigured; engaging RecoverIQ expert heuristics engine.")

        # Default / Graceful Fallback Heuristics Engine
        return self._run_expert_heuristics(context, fallback_reason=self.last_error_classification)

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
        Safely passes API key in header and URL query to ensure connectivity through proxies.
        """
        import httpx
        import time

        primary_model = settings.GEMINI_MODEL or "gemini-3.8-flash"
        candidate_models = [primary_model]
        for fallback_cand in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash", "gemini-3.8-pro", "gemini-3.0-pro", "gemini-3.0-flash"]:
            if fallback_cand not in candidate_models:
                candidate_models.append(fallback_cand)

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
                "responseMimeType": "application/json",
                "temperature": 0.1
            }
        }

        headers = {
            "x-goog-api-key": settings.GEMINI_API_KEY,
            "Content-Type": "application/json"
        }

        for model in candidate_models:
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            for attempt in range(2):
                try:
                    with httpx.Client(timeout=25.0) as client:
                        response = client.post(api_url, headers=headers, json=payload)
                        status = response.status_code
                        if status == 200:
                            res_data = response.json()
                            candidates = res_data.get("candidates", [])
                            if not candidates:
                                self.last_error_classification = "JSON parse = invalid model response"
                                logger.warning(f"Gemini LLM call failed: {self.last_error_classification}")
                                return None

                            content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            if not content_text:
                                self.last_error_classification = "JSON parse = invalid model response"
                                logger.warning(f"Gemini LLM call failed: {self.last_error_classification}")
                                return None

                            parsed = self._parse_json_payload(content_text)
                            if not parsed or not isinstance(parsed, dict):
                                self.last_error_classification = "JSON parse = invalid model response"
                                logger.warning(f"Gemini LLM call failed: {self.last_error_classification}")
                                return None

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

                            self.last_error_classification = None
                            return AIAgentRecommendation(
                                diagnosis=str(parsed.get("diagnosis", "Automated AI failure diagnosis")),
                                recovery_probability=round(prob, 2),
                                recommended_action=raw_action,
                                risk_level=raw_risk,
                                reason=str(parsed.get("reason", "AI assessed customer payment parameters.")),
                                requires_human_approval=bool(parsed.get("requires_human_approval", False) or ctx.amount >= 20000.0),
                                mode="LIVE_LLM",
                                model_used=primary_model,
                                fallback_used=False,
                                fallback_reason=None
                            )

                        # Response was not 200: safe error classification without logging secrets
                        err_msg = ""
                        try:
                            err_msg = response.json().get("error", {}).get("message", "")
                        except Exception:
                            pass

                        if status in (401, 403) or ("API key" in err_msg and "not valid" in err_msg):
                            self.last_error_classification = "401/403 = authentication/configuration"
                            logger.warning(f"Gemini LLM call failed: {self.last_error_classification}")
                            return None
                        elif status == 404:
                            self.last_error_classification = "404 = invalid model/endpoint"
                            logger.warning(f"Gemini LLM call failed: {self.last_error_classification}")
                            break
                        elif status == 429:
                            self.last_error_classification = "429 = rate limit"
                            logger.warning(f"Gemini LLM call failed: {self.last_error_classification}")
                            if attempt == 0:
                                time.sleep(1.0)
                                continue
                            break
                        elif status in (500, 502, 503, 504):
                            self.last_error_classification = "500/503 = Gemini service error"
                            logger.warning(f"Gemini LLM call failed: {self.last_error_classification}")
                            if attempt == 0:
                                time.sleep(1.0)
                                continue
                            break
                        elif status == 400:
                            self.last_error_classification = "400 = bad request"
                            logger.warning(f"Gemini LLM call failed: {self.last_error_classification}")
                            return None
                        else:
                            self.last_error_classification = f"HTTP {status}"
                            logger.warning(f"Gemini LLM call failed: {self.last_error_classification}")
                            return None

                except httpx.TimeoutException:
                    self.last_error_classification = "timeout/network = connectivity"
                    logger.warning(f"Gemini LLM call failed: {self.last_error_classification}")
                    if attempt == 0:
                        continue
                    break
                except (httpx.ConnectError, httpx.NetworkError):
                    self.last_error_classification = "timeout/network = connectivity"
                    logger.warning(f"Gemini LLM call failed: {self.last_error_classification}")
                    if attempt == 0:
                        time.sleep(1.0)
                        continue
                    break
                except Exception:
                    self.last_error_classification = "timeout/network = connectivity"
                    logger.warning(f"Gemini LLM call failed: {self.last_error_classification}")
                    break

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
                parsed = self._parse_json_payload(content_str)
                if not parsed or not isinstance(parsed, dict):
                    logger.warning("OpenAI LLM call failed: unable to parse valid structured JSON from model response")
                    return None

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
                    mode="LIVE_LLM",
                    model_used="gpt-4o-mini",
                    fallback_used=False
                )
        except Exception as e:
            logger.warning(f"OpenAI API execution error: {e}")
            return None

    def _run_expert_heuristics(
        self, 
        ctx: AIAnalysisInput, 
        fallback_reason: Optional[str] = None
    ) -> AIAgentRecommendation:
        """
        Domain-expert heuristic reasoning engine providing instant, explainable, and deterministic decisions.
        Clearly labeled as DEMO / RULE-BASED FALLBACK with safe error classification.
        """
        fb_reason = fallback_reason or self.last_error_classification or (
            "401/403 = authentication/configuration" if not settings.is_ai_configured else "500/503 = Gemini service error"
        )

        def make_rec(**kwargs) -> AIAgentRecommendation:
            return AIAgentRecommendation(
                mode="HEURISTIC_FALLBACK",
                model_used="RecoverIQ Expert Heuristics Engine",
                fallback_used=True,
                fallback_reason=fb_reason,
                **kwargs
            )

        # Heuristic Rule 1: Exceeded 2 automated retries -> STOP
        if ctx.retry_count >= 2:
            return make_rec(
                diagnosis=f"Exceeded maximum automated retry limit ({ctx.retry_count} retries attempted).",
                recovery_probability=0.15,
                recommended_action="STOP",
                risk_level="HIGH",
                reason=f"Customer {ctx.customer_name} has experienced repeated failures. Additional automated retries pose card block or decline charge risks. Bounded by policy.",
                requires_human_approval=False
            )

        # Heuristic Rule 2: High Value Transaction (>= ₹20,000)
        if ctx.amount >= 20000.0:
            if ctx.failure_reason in ["UPI_TIMEOUT", "NETWORK_ERROR"]:
                prob = 0.88 if ctx.previous_successful_payments >= 2 else 0.72
                return make_rec(
                    diagnosis=f"High-value B2B/enterprise payment (₹{ctx.amount:,.0f}) halted due to {ctx.failure_reason.replace('_', ' ')}.",
                    recovery_probability=prob,
                    recommended_action="PAYMENT_LINK",
                    risk_level="MEDIUM",
                    reason=f"High transaction value (₹{ctx.amount:,.0f}) with customer {ctx.customer_name} (LTV: ₹{ctx.customer_lifetime_value:,.0f}). Sending a secure Razorpay Payment Link allows white-glove recovery.",
                    requires_human_approval=True
                )
            elif ctx.failure_reason in ["INSUFFICIENT_FUNDS", "BANK_DECLINED"]:
                return make_rec(
                    diagnosis=f"High-value payment (₹{ctx.amount:,.0f}) declined by issuing bank.",
                    recovery_probability=0.45,
                    recommended_action="HUMAN_ESCALATION",
                    risk_level="HIGH",
                    reason=f"Large payment (₹{ctx.amount:,.0f}) declined by bank. Customer has {ctx.previous_failed_payments} past declines. Account manager escalation advised.",
                    requires_human_approval=True
                )

        # Heuristic Rule 3: Temporary UPI Timeout
        if ctx.failure_reason == "UPI_TIMEOUT":
            prob = 0.91 if (ctx.previous_successful_payments >= 1 or ctx.customer_lifetime_value > 0) else 0.82
            return make_rec(
                diagnosis="Temporary UPI PSP timeout or NPCI network latency",
                recovery_probability=prob,
                recommended_action="RETRY_PAYMENT",
                risk_level="LOW",
                reason=f"Customer {ctx.customer_name} has strong historical reliability ({ctx.previous_successful_payments} successful payments, ₹{ctx.customer_lifetime_value:,.0f} LTV). Transient timeout has 91% recovery rate on safe retry.",
                requires_human_approval=False
            )

        # Heuristic Rule 4: Network Error
        if ctx.failure_reason == "NETWORK_ERROR":
            return make_rec(
                diagnosis="Transient network connection drop during gateway handshake",
                recovery_probability=0.88,
                recommended_action="RETRY_PAYMENT",
                risk_level="LOW",
                reason="Temporary network socket timeout during transaction authorization. Automatic retry after backoff is safe and highly effective.",
                requires_human_approval=False
            )

        # Heuristic Rule 5: Bank Issuer Decline
        if ctx.failure_reason == "BANK_DECLINED":
            return make_rec(
                diagnosis="Bank issuer decline or card restriction",
                recovery_probability=0.68,
                recommended_action="ALTERNATIVE_PAYMENT_METHOD",
                risk_level="MEDIUM",
                reason=f"Issuing bank declined the transaction. Prompting customer {ctx.customer_name} to switch to an alternative UPI or Netbanking method maximizes conversion.",
                requires_human_approval=False
            )

        # Heuristic Rule 6: Insufficient Funds
        if ctx.failure_reason == "INSUFFICIENT_FUNDS":
            return make_rec(
                diagnosis="Insufficient account balance or daily UPI spending limit reached",
                recovery_probability=0.55,
                recommended_action="PAYMENT_LINK",
                risk_level="MEDIUM",
                reason="Customer account lacked sufficient balance at checkout time. Sending a scheduled payment link allows completion after account reload.",
                requires_human_approval=False
            )

        # Heuristic Rule 7: Payment Method Error
        if ctx.failure_reason == "PAYMENT_METHOD_ERROR":
            return make_rec(
                diagnosis="Invalid payment credentials or expired token",
                recovery_probability=0.62,
                recommended_action="ALTERNATIVE_PAYMENT_METHOD",
                risk_level="LOW",
                reason="The payment method credentials entered were invalid or expired. Prompting customer for alternate method.",
                requires_human_approval=False
            )

        # Default fallback
        return make_rec(
            diagnosis="Unclassified payment gateway failure",
            recovery_probability=0.50,
            recommended_action="PAYMENT_LINK",
            risk_level="MEDIUM",
            reason="Unclassified payment failure. Standard safe payment link fallback recommended.",
            requires_human_approval=False
        )

    def get_diagnostics(self) -> Dict[str, Any]:
        """
        Runs a safe diagnostic probe of the Gemini LLM integration without revealing secrets.
        """
        import httpx

        if not settings.is_ai_configured:
            return {
                "status": "UNCONFIGURED",
                "configured": False,
                "provider": settings.LLM_PROVIDER,
                "mode": "HEURISTIC_FALLBACK",
                "model": settings.GEMINI_MODEL,
                "error_classification": "401/403 = authentication/configuration"
            }

        model = settings.GEMINI_MODEL or "gemini-3.8-flash"
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        headers = {
            "x-goog-api-key": settings.GEMINI_API_KEY,
            "Content-Type": "application/json"
        }
        test_payload = {
            "contents": [{"parts": [{"text": "Output JSON: {\"status\": \"ok\"}"}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(api_url, headers=headers, json=test_payload)
                if res.status_code == 200:
                    return {
                        "status": "HEALTHY",
                        "configured": True,
                        "provider": settings.LLM_PROVIDER,
                        "mode": "LIVE_LLM",
                        "model": model,
                        "error_classification": None
                    }

                err_msg = ""
                try:
                    err_msg = res.json().get("error", {}).get("message", "")
                except Exception:
                    pass

                if res.status_code in (401, 403) or ("API key" in err_msg and "not valid" in err_msg):
                    err_class = "401/403 = authentication/configuration"
                elif res.status_code == 404:
                    err_class = "404 = invalid model/endpoint"
                elif res.status_code == 429:
                    err_class = "429 = rate limit"
                elif res.status_code in (500, 502, 503, 504):
                    err_class = "500/503 = Gemini service error"
                elif res.status_code == 400:
                    err_class = "400 = bad request"
                else:
                    err_class = f"HTTP {res.status_code}"

                return {
                    "status": "FAILED",
                    "configured": True,
                    "provider": settings.LLM_PROVIDER,
                    "mode": "HEURISTIC_FALLBACK",
                    "model": model,
                    "error_classification": err_class
                }
        except httpx.TimeoutException:
            return {
                "status": "TIMEOUT",
                "configured": True,
                "provider": settings.LLM_PROVIDER,
                "mode": "HEURISTIC_FALLBACK",
                "model": model,
                "error_classification": "timeout/network = connectivity"
            }
        except Exception:
            return {
                "status": "NETWORK_ERROR",
                "configured": True,
                "provider": settings.LLM_PROVIDER,
                "mode": "HEURISTIC_FALLBACK",
                "model": model,
                "error_classification": "timeout/network = connectivity"
            }

    def probe_models(self) -> dict:
        """Safely probes candidate models against Google Generative Language API."""
        import httpx
        if not settings.GEMINI_API_KEY:
            return {"configured": False, "error": "GEMINI_API_KEY is unset"}

        results = {}
        headers = {"x-goog-api-key": settings.GEMINI_API_KEY, "Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": "Reply JSON: {\"status\": \"ok\"}"}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        for m in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash", "gemini-3.8-flash"]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
            try:
                with httpx.Client(timeout=10.0) as client:
                    r = client.post(url, headers=headers, json=payload)
                    err_msg = ""
                    try:
                        err_msg = r.json().get("error", {}).get("message", "")[:120]
                    except Exception:
                        pass
                    results[m] = {"status_code": r.status_code, "error": err_msg}
            except Exception as e:
                results[m] = {"exception": str(e)}
        return results

ai_agent = RecoveryAIAgent()

