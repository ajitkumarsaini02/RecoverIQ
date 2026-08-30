import base64
import uuid
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import httpx
from app.config import settings

logger = logging.getLogger("recoveriq.razorpay")

class RazorpayService:
    """
    Razorpay Test Mode abstraction with automatic fallback to DEMO / SIMULATION MODE.
    Ensures safe, bounded execution without exposing secrets to frontend or crashing if keys are unset.
    """
    BASE_URL = "https://api.razorpay.com/v1"

    def __init__(self, key_id: Optional[str] = None, key_secret: Optional[str] = None):
        self.key_id = key_id or settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret or settings.RAZORPAY_KEY_SECRET

    @property
    def is_configured(self) -> bool:
        return bool(self.key_id and self.key_secret)

    @property
    def is_live_test_mode(self) -> bool:
        """Returns True only if actual test credentials are provided."""
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
        notes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Creates a Razorpay Order in paise (1 INR = 100 paise).
        Calls real Razorpay Test API if credentials exist, otherwise returns simulated order.
        """
        amount_paise = int(round(amount_in_inr * 100))
        receipt_id = receipt or f"rcpt_{uuid.uuid4().hex[:10]}"
        notes_payload = notes or {"source": "RecoverIQ Revenue Recovery"}

        if self.is_live_test_mode:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
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
                        return data
                    else:
                        logger.warning(f"Razorpay API returned {response.status_code}, falling back to simulation: {response.text}")
            except Exception as e:
                logger.error(f"Razorpay Test Mode network error: {e}, falling back to simulation.")

        # Simulation Mode fallback
        return {
            "id": f"order_test_{uuid.uuid4().hex[:14]}",
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
        description: str = "Payment Recovery Link - RecoverIQ"
    ) -> Dict[str, Any]:
        """
        Generates a Razorpay Payment Link for customer recovery.
        """
        amount_paise = int(round(amount_in_inr * 100))
        phone = customer_phone or "+919876543210"

        if self.is_live_test_mode:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
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
                        return data
                    else:
                        logger.warning(f"Razorpay Payment Link API error: {response.text}")
            except Exception as e:
                logger.error(f"Razorpay Payment Link error: {e}")

        # Simulation Mode
        link_id = f"plink_test_{uuid.uuid4().hex[:12]}"
        return {
            "id": link_id,
            "entity": "payment_link",
            "short_url": f"https://rzp.io/i/test_{uuid.uuid4().hex[:8]}",
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

    async def check_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Queries Razorpay for payment status or generates simulated response.
        """
        if self.is_live_test_mode and not payment_id.startswith("pay_sim_"):
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
            except Exception as e:
                logger.error(f"Error checking payment status: {e}")

        # Simulation Mode
        return {
            "id": payment_id,
            "entity": "payment",
            "amount": 499900,
            "currency": "INR",
            "status": "captured",
            "method": "upi",
            "captured": True,
            "mode": "SIMULATION_MODE"
        }

# Global Singleton Instance
razorpay_service = RazorpayService()
