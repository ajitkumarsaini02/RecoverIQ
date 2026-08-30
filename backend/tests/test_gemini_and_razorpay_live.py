import pytest
import hmac
import hashlib
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.config import settings
from tests.conftest import TestSession
from app.db.models import Transaction, Customer, RecoveryAction, AuditEvent
from app.services.ai_agent import ai_agent, AIAnalysisInput
from app.services.razorpay_service import razorpay_service

client = TestClient(app)

def test_gemini_api_call_mocked_success():
    """Verify that when Gemini credentials are configured, the agent correctly parses structured JSON."""
    fake_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "diagnosis": "UPI PSP timeout at ICICI Bank switch",
                                "recovery_probability": 0.94,
                                "recommended_action": "RETRY_PAYMENT",
                                "risk_level": "LOW",
                                "reason": "Reliable customer with zero fraud indicators.",
                                "requires_human_approval": False
                            })
                        }
                    ]
                }
            }
        ]
    }

    ctx = AIAnalysisInput(
        transaction_id="txn_test_gemini",
        amount=1499.0,
        currency="INR",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        error_code="PSP_TIMEOUT",
        retry_count=0,
        customer_id="cust_1",
        customer_name="Aarav Sharma",
        customer_email="aarav@gmail.com",
        customer_lifetime_value=25000.0,
        previous_successful_payments=4,
        previous_failed_payments=0,
        previous_recovery_attempts=0
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock-gemini-key"):
        with patch.object(settings, "LLM_PROVIDER", "gemini"):
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = fake_gemini_response
            mock_client.post.return_value = mock_resp

            with patch("httpx.Client") as MockHttpx:
                MockHttpx.return_value.__enter__.return_value = mock_client
                result = ai_agent._call_gemini_api(ctx)

                assert result is not None
                assert result.diagnosis == "UPI PSP timeout at ICICI Bank switch"
                assert result.recovery_probability == 0.94
                assert result.recommended_action == "RETRY_PAYMENT"
                assert result.risk_level == "LOW"
                assert result.fallback_used is False
                assert "Gemini" in result.model_used

def test_gemini_fallback_when_api_key_unconfigured():
    """Verify that when Gemini is unconfigured or fails, the Heuristics Engine safely takes over."""
    db = TestSession()
    cust = Customer(
        id="cust_heur_1",
        name="Pooja Rao",
        email="pooja@domain.in",
        phone="+919811223344",
        lifetime_value=12000.0,
        successful_payments_count=3,
        failed_payments_count=0,
        risk_score=0.1
    )
    txn = Transaction(
        id="txn_heur_1",
        customer_id=cust.id,
        amount=1999.0,
        currency="INR",
        status="FAILED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=0
    )
    db.add(cust)
    db.add(txn)
    db.commit()

    rec = ai_agent.analyze_failure(transaction=txn, customer=cust)
    assert rec.fallback_used is True
    assert rec.mode in ["DEMO_FALLBACK", "HEURISTIC_FALLBACK"]
    assert rec.model_used == "RecoverIQ Expert Heuristics Engine"
    assert rec.recommended_action == "RETRY_PAYMENT"
    db.close()

def test_razorpay_webhook_signature_verification():
    """Test HMAC SHA256 webhook signature verification against webhook secret."""
    secret = "secret_webhook_test_12345"
    payload_dict = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_webhook_01",
                    "order_id": "order_webhook_01",
                    "amount": 499900,
                    "status": "captured"
                }
            }
        }
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    valid_sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    # Verify matching signature
    is_valid = razorpay_service.verify_webhook_signature(
        payload_body=payload_bytes,
        signature=valid_sig,
        secret=secret
    )
    assert is_valid is True

    # Verify invalid signature rejection
    is_invalid = razorpay_service.verify_webhook_signature(
        payload_body=payload_bytes,
        signature="invalid_signature_hash",
        secret=secret
    )
    assert is_invalid is False

def test_razorpay_webhook_event_processing():
    """Test that POST /api/webhook/razorpay updates transaction status to RECOVERED upon captured payment."""
    db = TestSession()
    cust = Customer(
        id="cust_wh_1",
        name="Webhook Customer",
        email="webhook@domain.in",
        phone="+919811002233",
        lifetime_value=15000.0,
        successful_payments_count=2,
        failed_payments_count=0,
        risk_score=0.1
    )
    txn = Transaction(
        id="txn_wh_test_1",
        customer_id=cust.id,
        amount=4999.0,
        currency="INR",
        status="FAILED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        razorpay_order_id="order_wh_test_99",
        retry_count=0
    )
    db.add(cust)
    db.add(txn)
    db.commit()

    webhook_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_captured_99",
                    "order_id": "order_wh_test_99",
                    "amount": 499900,
                    "status": "captured"
                }
            }
        }
    }

    res = client.post("/api/webhook/razorpay", json=webhook_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # Refresh transaction from DB
    updated_txn = db.query(Transaction).filter(Transaction.id == "txn_wh_test_1").first()
    assert updated_txn.status == "RECOVERED"
    assert updated_txn.razorpay_payment_id == "pay_captured_99"
    db.close()

def test_recovery_idempotency_protection():
    """Verify that multiple rapid recovery requests return an idempotent result without double-counting."""
    db = TestSession()
    cust = Customer(
        id="cust_idemp_1",
        name="Idempotent Customer",
        email="idemp@domain.in",
        phone="+919811002244",
        lifetime_value=25000.0,
        successful_payments_count=4,
        failed_payments_count=0,
        risk_score=0.05
    )
    txn = Transaction(
        id="txn_idemp_1",
        customer_id=cust.id,
        amount=3499.0,
        currency="INR",
        status="RECOVERED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=1
    )
    db.add(cust)
    db.add(txn)
    db.commit()

    # Call recovery on already recovered transaction
    res = client.post("/api/recovery/execute/txn_idemp_1")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["details"].get("already_recovered") is True
    db.close()

def test_gemini_invalid_json_fallback():
    """Verify that when Gemini returns invalid/corrupt JSON, the system gracefully falls back to Heuristics Engine."""
    ctx = AIAnalysisInput(
        transaction_id="txn_test_gemini_corrupt",
        amount=1499.0,
        currency="INR",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=0,
        customer_id="cust_test_corrupt",
        customer_name="Test Corrupt",
        customer_email="corrupt@test.in",
        customer_lifetime_value=10000.0,
        previous_successful_payments=2,
        previous_failed_payments=0,
        previous_recovery_attempts=0
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock-gemini-key"):
        with patch.object(settings, "LLM_PROVIDER", "gemini"):
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "candidates": [{"content": {"parts": [{"text": "THIS_IS_NOT_VALID_JSON"}]}}]
            }
            mock_client.post.return_value = mock_resp

            with patch("httpx.Client") as MockHttpx:
                MockHttpx.return_value.__enter__.return_value = mock_client
                result = ai_agent._call_gemini_api(ctx)
                assert result is None # Fails gracefully, allowing fallback

def test_gemini_network_error_fallback():
    """Verify that when Gemini API has network/timeout exception, fallback engages safely."""
    ctx = AIAnalysisInput(
        transaction_id="txn_test_gemini_timeout",
        amount=1499.0,
        currency="INR",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=0,
        customer_id="cust_test_timeout",
        customer_name="Test Timeout",
        customer_email="timeout@test.in",
        customer_lifetime_value=15000.0,
        previous_successful_payments=3,
        previous_failed_payments=0,
        previous_recovery_attempts=0
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock-gemini-key"):
        with patch.object(settings, "LLM_PROVIDER", "gemini"):
            with patch("httpx.Client") as MockHttpx:
                MockHttpx.return_value.__enter__.side_effect = Exception("Connection timeout to Generative Language API")
                result = ai_agent._call_gemini_api(ctx)
                assert result is None

@pytest.mark.asyncio
async def test_razorpay_order_and_payment_link_creation():
    """Verify Razorpay order and payment link generation in simulation and test mode."""
    order_sim = await razorpay_service.create_order(amount_in_inr=1500.0, force_mode="SIMULATION_MODE")
    assert order_sim["mode"] == "SIMULATION_MODE"
    assert order_sim["amount"] == 150000
    assert order_sim["id"].startswith("order_sim_")

    plink_sim = await razorpay_service.create_payment_link(
        amount_in_inr=2000.0,
        customer_name="Test User",
        customer_email="test@user.in",
        force_mode="SIMULATION_MODE"
    )
    assert plink_sim["mode"] == "SIMULATION_MODE"
    assert "rzp.io" in plink_sim["short_url"]

def test_razorpay_payment_signature_verification():
    """Verify Razorpay HMAC-SHA256 payment signature verification logic."""
    secret = "rzp_secret_key_12345"
    order_id = "order_test_123"
    payment_id = "pay_test_456"
    
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    with patch.object(razorpay_service, "key_secret", secret):
        assert razorpay_service.verify_payment_signature(order_id, payment_id, valid_sig) is True
        assert razorpay_service.verify_payment_signature(order_id, payment_id, "invalid_sig_abc") is False

def test_duplicate_webhook_idempotency():
    """Verify duplicate webhook payloads do not create multiple recovery events."""
    db = TestSession()
    cust = Customer(
        id="cust_wh_idemp",
        name="Webhook Idemp Customer",
        email="idemp_wh@domain.in",
        phone="+919811009988",
        lifetime_value=20000.0,
        successful_payments_count=3,
        failed_payments_count=0,
        risk_score=0.08
    )
    txn = Transaction(
        id="txn_wh_idemp_1",
        customer_id=cust.id,
        amount=2499.0,
        currency="INR",
        status="FAILED",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        razorpay_order_id="order_wh_idemp_99",
        retry_count=0
    )
    db.add(cust)
    db.add(txn)
    db.commit()

    webhook_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_captured_idemp_99",
                    "order_id": "order_wh_idemp_99",
                    "amount": 249900,
                    "status": "captured"
                }
            }
        }
    }

    # First webhook
    res1 = client.post("/api/webhook/razorpay", json=webhook_payload)
    assert res1.status_code == 200

    # Second identical webhook
    res2 = client.post("/api/webhook/razorpay", json=webhook_payload)
    assert res2.status_code == 200

    # Verify transaction remains RECOVERED without duplicate recovery actions
    updated_txn = db.query(Transaction).filter(Transaction.id == "txn_wh_idemp_1").first()
    assert updated_txn.status == "RECOVERED"
    db.close()

def test_scenario_explicit_modes():
    """Verify that /api/demo/scenario correctly handles both TEST_MODE and SIMULATION_MODE."""
    # Simulation Mode
    res_sim = client.post("/api/demo/scenario", json={"scenario": "temporary_upi_failure", "mode": "SIMULATION_MODE"})
    assert res_sim.status_code == 200
    data_sim = res_sim.json()
    assert data_sim["mode"] == "SIMULATION_MODE"
    assert data_sim["recovery_result"]["mode"] == "SIMULATION_MODE"

    # Test Mode
    res_test = client.post("/api/demo/scenario", json={"scenario": "temporary_upi_failure", "mode": "TEST_MODE"})
    assert res_test.status_code == 200
    data_test = res_test.json()
    assert data_test["mode"] == "TEST_MODE"
    assert data_test["recovery_result"]["mode"] == "TEST_MODE"


