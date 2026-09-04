import base64
import uuid
import json
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import httpx
from app.config import settings

logger = logging.getLogger("recoveriq.razorpay")

class RazorpayService:
    """
    Razorpay Test Mode abstraction with independent payment verification
    and separate explicit SIMULATION MODE.
    Ensures safe, bounded execution without exposing secrets to frontend.
    """
    BASE_URL = "https://api.razorpay.com/v1"

    def __init__(self, key_id: Optional[str] = None, key_secret: Optional[str] = None, webhook_secret: Optional[str] = None):
        self.key_id = key_id or settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret or settings.RAZORPAY_KEY_SECRET
        self.webhook_secret = webhook_secret or settings.RAZORPAY_WEBHOOK_SECRET

    @property
    def is_configured(self) -> bool:
        return bool(self.key_id and self.key_secret)

    @property
    def is_live_test_mode(self) -> bool:
        """Returns True only if actual Razorpay test credentials are provided."""
        return bool(
            self.is_configured
            and not self.key_id.startswith("rzp_test_placeholder")
            and not self.key_secret.startswith("placeholder")
        )

    @property
    def current_mode_label(self) -> str:
        return "TEST_MODE" if self.is_live_test_mode else "SIMULATION_MODE"

    def _get_auth_header(self) -> Dict[str, str]:
        token = base64.b64encode(f"{self.key_id}:{self.key_secret}".encode()).decode()
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json"
        }

    async def create_order(
        self, 
        amount_in_inr: float, 
        receipt: Optional[str] = None, 
        notes: Optional[Dict[str, Any]] = None,
        force_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a Razorpay Order in paise (1 INR = 100 paise).
        Calls real Razorpay Test API if in TEST_MODE and configured, otherwise returns simulated order.
        """
        amount_paise = int(round(amount_in_inr * 100))
        receipt_id = receipt or f"rcpt_{uuid.uuid4().hex[:10]}"
        notes_payload = notes or {"source": "RecoverIQ Revenue Recovery"}
        requested_mode = force_mode or self.current_mode_label

        if requested_mode == "TEST_MODE":
            if not self.is_live_test_mode:
                return {
                    "error": "Razorpay keys are unconfigured or placeholder values, but TEST_MODE was requested.",
                    "mode": "TEST_MODE",
                    "status": "failed"
                }

        if requested_mode == "TEST_MODE" and self.is_live_test_mode:
            try:
                async with httpx.AsyncClient(timeout=12.0) as client:
                    response = await client.post(
                        f"{self.BASE_URL}/orders",
                        headers=self._get_auth_header(),
                        json={
                            "amount": amount_paise,
                            "currency": "INR",
                            "receipt": receipt_id,
                            "notes": notes_payload
                        }
                    )
                    if response.status_code in [200, 201]:
                        data = response.json()
                        data["mode"] = "TEST_MODE"
                        logger.info(f"Razorpay Test Order created: {data.get('id')}")
                        return data
                    else:
                        logger.error(f"Razorpay Order API returned HTTP {response.status_code}: {response.text[:200]}")
                        return {
                            "error": f"Razorpay API error ({response.status_code})",
                            "details": response.text[:200],
                            "mode": "TEST_MODE",
                            "status": "failed"
                        }
            except Exception as e:
                logger.error(f"Razorpay Test Mode network error: {e}")
                return {
                    "error": str(e),
                    "mode": "TEST_MODE",
                    "status": "failed"
                }

        # Simulation Mode fallback
        return {
            "id": f"order_sim_{uuid.uuid4().hex[:14]}",
            "entity": "order",
            "amount": amount_paise,
            "amount_paid": 0,
            "amount_due": amount_paise,
            "currency": "INR",
            "receipt": receipt_id,
            "status": "created",
            "attempts": 0,
            "notes": notes_payload,
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "mode": "SIMULATION_MODE"
        }

    async def create_payment_link(
        self,
        amount_in_inr: float,
        customer_name: str,
        customer_email: str,
        customer_phone: Optional[str] = None,
        description: str = "Payment Recovery Link - RecoverIQ",
        force_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates a real Razorpay Payment Link in Test Mode or returns simulated link.
        """
        amount_paise = int(round(amount_in_inr * 100))
        raw_phone = customer_phone or "+919876543210"
        phone = "".join(c for c in raw_phone if c.isdigit() or c == "+")
        requested_mode = force_mode or self.current_mode_label

        if requested_mode == "TEST_MODE":
            if not self.is_live_test_mode:
                return {
                    "error": "Razorpay keys are unconfigured or placeholder values, but TEST_MODE was requested.",
                    "mode": "TEST_MODE",
                    "status": "failed"
                }

        if requested_mode == "TEST_MODE" and self.is_live_test_mode:
            try:
                async with httpx.AsyncClient(timeout=12.0) as client:
                    response = await client.post(
                        f"{self.BASE_URL}/payment_links",
                        headers=self._get_auth_header(),
                        json={
                            "amount": amount_paise,
                            "currency": "INR",
                            "accept_partial": False,
                            "description": description,
                            "customer": {
                                "name": customer_name,
                                "email": customer_email,
                                "contact": phone
                            },
                            "notify": {"sms": False, "email": True},
                            "reminder_enable": True,
                            "notes": {"recovered_by": "RecoverIQ_Agent"}
                        }
                    )
                    if response.status_code in [200, 201]:
                        data = response.json()
                        data["mode"] = "TEST_MODE"
                        logger.info(f"Razorpay Payment Link generated: {data.get('short_url')}")
                        return data
                    else:
                        logger.error(f"Razorpay Payment Link error HTTP {response.status_code}: {response.text[:200]}")
                        return {
                            "error": f"Razorpay Payment Link error ({response.status_code})",
                            "mode": "TEST_MODE",
                            "status": "failed"
                        }
            except Exception as e:
                logger.error(f"Razorpay Payment Link exception: {e}")
                return {
                    "error": str(e),
                    "mode": "TEST_MODE",
                    "status": "failed"
                }

        # Simulation Mode
        link_id = f"plink_sim_{uuid.uuid4().hex[:12]}"
        return {
            "id": link_id,
            "entity": "payment_link",
            "short_url": f"https://rzp.io/i/sim_{uuid.uuid4().hex[:8]}",
            "amount": amount_paise,
            "currency": "INR",
            "status": "created",
            "description": description,
            "customer": {
                "name": customer_name,
                "email": customer_email,
                "contact": phone
            },
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "mode": "SIMULATION_MODE"
        }

    async def fetch_payment(self, payment_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetches payment details directly from Razorpay Test API.
        """
        if not payment_id:
            return {"status": "not_found", "mode": self.current_mode_label}

        if self.is_live_test_mode:
            if payment_id.startswith("pay_sim_"):
                return {
                    "status": "failed",
                    "error": "Cannot fetch simulated payment in live TEST_MODE",
                    "mode": "TEST_MODE",
                    "captured": False
                }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        f"{self.BASE_URL}/payments/{payment_id}",
                        headers=self._get_auth_header()
                    )
                    if response.status_code == 200:
                        data = response.json()
                        data["mode"] = "TEST_MODE"
                        return data
                    else:
                        return {
                            "status": "failed",
                            "error": f"Razorpay API returned HTTP {response.status_code}",
                            "mode": "TEST_MODE",
                            "captured": False
                        }
            except Exception as e:
                logger.error(f"Error checking payment {payment_id}: {e}")
                return {
                    "status": "failed",
                    "error": str(e),
                    "mode": "TEST_MODE",
                    "captured": False
                }

        # Simulation Sandbox Mode
        is_sim_captured = payment_id.startswith("pay_sim_") or payment_id.startswith("pay_captured_")
        return {
            "id": payment_id,
            "entity": "payment",
            "amount": 499900,
            "currency": "INR",
            "status": "captured" if is_sim_captured else "failed",
            "method": "upi",
            "captured": is_sim_captured,
            "mode": "SIMULATION_MODE"
        }

    async def fetch_order_payments(self, order_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetches all payments associated with a Razorpay Order to verify capture.
        """
        if not order_id:
            return []

        if self.is_live_test_mode and not order_id.startswith("order_sim_"):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        f"{self.BASE_URL}/orders/{order_id}/payments",
                        headers=self._get_auth_header()
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return data.get("items", [])
            except Exception as e:
                logger.error(f"Error fetching payments for order {order_id}: {e}")
        return []

    def verify_payment_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        """
        Verifies Razorpay payment signature using HMAC SHA256.
        """
        if not self.key_secret or not order_id or not payment_id or not signature:
            return False
        try:
            msg = f"{order_id}|{payment_id}".encode("utf-8")
            expected = hmac.new(self.key_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, signature)
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

    def verify_webhook_signature(self, payload_body: bytes, signature: str, secret: Optional[str] = None) -> bool:
        """
        Verifies Razorpay Webhook signature using HMAC SHA256.
        """
        webhook_key = secret or self.webhook_secret or self.key_secret
        if not webhook_key or not signature:
            return False
        try:
            expected = hmac.new(webhook_key.encode("utf-8"), payload_body, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, signature)
        except Exception as e:
            logger.error(f"Webhook signature verification exception: {e}")
            return False

# Global Singleton Instance
razorpay_service = RazorpayService()

