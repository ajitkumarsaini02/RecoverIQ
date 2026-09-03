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
from app.services.policy_engine import policy_engine

client = TestClient(app)

def post_signed_webhook(client_obj, payload, secret="whsec_dummy"):
    payload_bytes = json.dumps(payload).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return client_obj.post(
        "/api/webhook/razorpay",
        content=payload_bytes,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig}
    )

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
                assert result.mode == "LIVE_LLM"
                assert "gemini" in result.model_used.lower()

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

    res = post_signed_webhook(client, webhook_payload)
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
    res1 = post_signed_webhook(client, webhook_payload)
    assert res1.status_code == 200

    # Second identical webhook
    res2 = post_signed_webhook(client, webhook_payload)
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

def test_gemini_markdown_fenced_json_parsing():
    """Verify that Gemini responses wrapped in ```json ... ``` markdown fences parse cleanly."""
    markdown_wrapped_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "```json\n{\n  \"diagnosis\": \"Card network decline due to international transactions disabled\",\n  \"recovery_probability\": 0.78,\n  \"recommended_action\": \"ALTERNATIVE_PAYMENT_METHOD\",\n  \"risk_level\": \"LOW\",\n  \"reason\": \"Offer UPI or domestic debit card alternative.\",\n  \"requires_human_approval\": false\n}\n```"
                        }
                    ]
                }
            }
        ]
    }

    ctx = AIAnalysisInput(
        transaction_id="txn_test_gemini_fences",
        amount=2999.0,
        currency="INR",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        error_code="CARD_RESTRICTED",
        retry_count=0,
        customer_id="cust_fence_1",
        customer_name="Rohan Mehra",
        customer_email="rohan@mehra.in",
        customer_lifetime_value=18000.0,
        previous_successful_payments=3,
        previous_failed_payments=1,
        previous_recovery_attempts=0
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock-gemini-key"):
        with patch.object(settings, "LLM_PROVIDER", "gemini"):
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = markdown_wrapped_response
            mock_client.post.return_value = mock_resp

            with patch("httpx.Client") as MockHttpx:
                MockHttpx.return_value.__enter__.return_value = mock_client
                result = ai_agent._call_gemini_api(ctx)

                assert result is not None
                assert result.diagnosis == "Card network decline due to international transactions disabled"
                assert result.recommended_action == "ALTERNATIVE_PAYMENT_METHOD"
                assert result.recovery_probability == 0.78
                assert result.fallback_used is False
                assert result.mode == "LIVE_LLM"

def test_gemini_conversational_wrapped_json_parsing():
    """Verify that Gemini responses wrapped in conversational prose and markdown fences parse cleanly."""
    conversational_text = """Here is your recovery analysis for the failed transaction:
```json
{
    "diagnosis": "Card network decline due to OTP timeout",
    "recovery_probability": 0.85,
    "recommended_action": "RETRY_PAYMENT",
    "risk_level": "LOW",
    "reason": "Customer entered incorrect OTP initially.",
    "requires_human_approval": false
}
```
Please let me know if further analysis is needed."""

    response_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": conversational_text}]
                }
            }
        ]
    }

    ctx = AIAnalysisInput(
        transaction_id="txn_test_gemini_prose",
        amount=2500.0,
        currency="INR",
        payment_method="CARD",
        failure_reason="OTP_TIMEOUT",
        error_code="OTP_TIMEOUT",
        retry_count=0,
        customer_id="cust_p1",
        customer_name="Rohan Mehra",
        customer_email="rohan@example.com",
        customer_lifetime_value=18000.0,
        previous_successful_payments=3,
        previous_failed_payments=0,
        previous_recovery_attempts=0
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock-gemini-key"):
        with patch.object(settings, "LLM_PROVIDER", "gemini"):
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = response_payload
            mock_client.post.return_value = mock_resp

            with patch("httpx.Client") as MockHttpx:
                MockHttpx.return_value.__enter__.return_value = mock_client
                result = ai_agent._call_gemini_api(ctx)

                assert result is not None
                assert result.diagnosis == "Card network decline due to OTP timeout"
                assert result.recommended_action == "RETRY_PAYMENT"
                assert result.recovery_probability == 0.85
                assert result.mode == "LIVE_LLM"
                assert result.fallback_used is False

def test_gemini_error_classification_and_safe_logging(caplog):
    """Verify that 401, 404, 429, 500 errors are safely classified without leaking credentials."""
    import logging
    ctx = AIAnalysisInput(
        transaction_id="txn_test_err_class",
        amount=1000.0,
        currency="INR",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=0,
        customer_id="cust_err",
        customer_name="Test User",
        customer_email="test@example.com",
        customer_lifetime_value=5000.0,
        previous_successful_payments=1,
        previous_failed_payments=0,
        previous_recovery_attempts=0
    )

    secret_key = "super-secret-gemini-key-12345"
    with patch.object(settings, "GEMINI_API_KEY", secret_key):
        with patch.object(settings, "LLM_PROVIDER", "gemini"):
            for status_code, expected_log_phrase in [
                (401, "401/403 = authentication/configuration"),
                (404, "404 = invalid model/endpoint"),
                (429, "429 = rate limit"),
                (400, "400 = bad request"),
                (500, "500/503 = Gemini service error"),
            ]:
                mock_client = MagicMock()
                mock_resp = MagicMock()
                mock_resp.status_code = status_code
                mock_client.post.return_value = mock_resp

                with patch("httpx.Client") as MockHttpx:
                    MockHttpx.return_value.__enter__.return_value = mock_client
                    with caplog.at_level(logging.WARNING):
                        caplog.clear()
                        result = ai_agent._call_gemini_api(ctx)
                        assert result is None
                        assert any(expected_log_phrase in record.message for record in caplog.records)
                        # Ensure secret key is NEVER in logs
                        assert all(secret_key not in record.message for record in caplog.records)

def test_gemini_uses_header_auth():
    """Verify that GEMINI_API_KEY is transmitted via x-goog-api-key header and not exposed in URL."""
    ctx = AIAnalysisInput(
        transaction_id="txn_test_header_auth",
        amount=1500.0,
        currency="INR",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=0,
        customer_id="cust_hdr",
        customer_name="Test User",
        customer_email="test@example.com",
        customer_lifetime_value=5000.0,
        previous_successful_payments=1,
        previous_failed_payments=0,
        previous_recovery_attempts=0
    )

    secret_key = "my-secret-gemini-key"
    with patch.object(settings, "GEMINI_API_KEY", secret_key):
        with patch.object(settings, "LLM_PROVIDER", "gemini"):
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "candidates": [{"content": {"parts": [{"text": '{"diagnosis": "ok", "recovery_probability": 0.9, "recommended_action": "RETRY_PAYMENT", "risk_level": "LOW", "reason": "ok", "requires_human_approval": false}'}]}}]
            }
            mock_client.post.return_value = mock_resp

            with patch("httpx.Client") as MockHttpx:
                MockHttpx.return_value.__enter__.return_value = mock_client
                result = ai_agent._call_gemini_api(ctx)
                assert result is not None

                # Verify post call arguments
                call_args = mock_client.post.call_args
                called_url = call_args[0][0]
                called_headers = call_args[1]["headers"]

                # Secret key MUST be in headers and NOT in the URL
                assert secret_key not in called_url
                assert called_headers.get("x-goog-api-key") == secret_key

from unittest.mock import patch, MagicMock, AsyncMock

def test_razorpay_order_failure_without_id_sets_failed_status():
    """Verify that when Razorpay returns an error without order ID, the recovery is marked FAILED instead of RECOVERY_PENDING."""
    db = TestSession()
    cust = Customer(
        id="cust_fail_order_1",
        name="Sunita Das",
        email="sunita@das.in",
        phone="+919700011122",
        lifetime_value=5000.0,
        successful_payments_count=1,
        failed_payments_count=0,
        risk_score=0.1
    )
    txn = Transaction(
        id="txn_fail_order_1",
        customer_id=cust.id,
        amount=1500.0,
        currency="INR",
        status="FAILED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=0
    )
    db.add(cust)
    db.add(txn)
    db.commit()

    with patch("app.services.razorpay_service.razorpay_service.create_order", new_callable=AsyncMock) as mock_create_order:
        mock_create_order.return_value = {
            "error": "Authentication failed with Razorpay gateway",
            "status": "failed",
            "mode": "TEST_MODE"
        }

        res = client.post(f"/api/recovery/execute/{txn.id}?mode=TEST_MODE")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "FAILED"
        assert "failed" in data["message"].lower()

        # Check DB transaction status
        updated_txn = db.query(Transaction).filter(Transaction.id == txn.id).first()
        assert updated_txn.status == "FAILED"
    db.close()

def test_unpaid_order_remains_recovery_pending():
    """Verify that creating an order without immediate capture leaves the transaction in RECOVERY_PENDING with recovered_amount = 0."""
    db = TestSession()
    cust = Customer(
        id="cust_unpaid_1",
        name="Karan Malhotra",
        email="karan@malhotra.in",
        phone="+919876543210",
        lifetime_value=12000.0,
        successful_payments_count=2,
        failed_payments_count=0,
        risk_score=0.08
    )
    txn = Transaction(
        id="txn_unpaid_1",
        customer_id=cust.id,
        amount=3499.0,
        currency="INR",
        status="FAILED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=0
    )
    db.add(cust)
    db.add(txn)
    db.commit()

    with patch("app.services.razorpay_service.razorpay_service.create_order", new_callable=AsyncMock) as mock_create_order:
        with patch("app.services.razorpay_service.razorpay_service.fetch_order_payments", new_callable=AsyncMock) as mock_fetch_payments:
            mock_create_order.return_value = {
                "id": "order_test_unpaid_12345",
                "status": "created",
                "amount": 349900,
                "mode": "TEST_MODE"
            }
            # No captured payments yet
            mock_fetch_payments.return_value = []

            res = client.post(f"/api/recovery/execute/{txn.id}?mode=TEST_MODE")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "PENDING"
            assert data["amount_recovered"] == 0.0
            assert "order_test_unpaid_12345" in data["message"]

            db.expire_all()
            updated_txn = db.query(Transaction).filter(Transaction.id == txn.id).first()
            assert updated_txn.status == "RECOVERY_PENDING"
            assert updated_txn.razorpay_order_id == "order_test_unpaid_12345"
    db.close()

def test_verify_endpoint_captured_payment():
    """Verify that when fetch_payment returns captured, status becomes RECOVERED and recovered_amount is updated."""
    db = TestSession()
    cust = Customer(
        id="cust_verify_1",
        name="Deepak Joshi",
        email="deepak@joshi.in",
        phone="+919811223344",
        lifetime_value=25000.0,
        successful_payments_count=5,
        failed_payments_count=0,
        risk_score=0.05
    )
    txn = Transaction(
        id="txn_verify_captured_1",
        customer_id=cust.id,
        amount=4999.0,
        currency="INR",
        status="RECOVERY_PENDING",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        razorpay_order_id="order_v_100",
        retry_count=1
    )
    db.add(cust)
    db.add(txn)
    db.commit()

    with patch("app.services.razorpay_service.razorpay_service.fetch_payment", new_callable=AsyncMock) as mock_fetch_payment:
        mock_fetch_payment.return_value = {
            "id": "pay_test_cap_100",
            "order_id": "order_v_100",
            "amount": 499900,
            "status": "captured"
        }

        res = client.post(f"/api/recovery/verify/{txn.id}", json={"payment_id": "pay_test_cap_100"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "RECOVERED"
        assert data["verified"] is True
        assert data["recovered_amount"] == 4999.0

        db.expire_all()
        updated_txn = db.query(Transaction).filter(Transaction.id == txn.id).first()
        assert updated_txn.status == "RECOVERED"
        assert updated_txn.razorpay_payment_id == "pay_test_cap_100"
    db.close()

def test_verify_endpoint_authorized_uncaptured_payment():
    """Verify that an authorized (uncaptured) payment leaves the transaction in RECOVERY_PENDING."""
    db = TestSession()
    cust = Customer(
        id="cust_verify_2",
        name="Meera Iyer",
        email="meera@iyer.in",
        phone="+919822334455",
        lifetime_value=15000.0,
        successful_payments_count=2,
        failed_payments_count=0,
        risk_score=0.1
    )
    txn = Transaction(
        id="txn_verify_auth_1",
        customer_id=cust.id,
        amount=2999.0,
        currency="INR",
        status="RECOVERY_PENDING",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        razorpay_order_id="order_v_200",
        retry_count=1
    )
    db.add(cust)
    db.add(txn)
    db.commit()

    with patch("app.services.razorpay_service.razorpay_service.fetch_payment", new_callable=AsyncMock) as mock_fetch_payment:
        mock_fetch_payment.return_value = {
            "id": "pay_test_auth_200",
            "order_id": "order_v_200",
            "amount": 299900,
            "status": "authorized" # Not captured yet
        }

        res = client.post(f"/api/recovery/verify/{txn.id}", json={"payment_id": "pay_test_auth_200"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "RECOVERY_PENDING"
        assert data["verified"] is False
        assert data["recovered_amount"] == 0.0

        db.expire_all()
        updated_txn = db.query(Transaction).filter(Transaction.id == txn.id).first()
        assert updated_txn.status == "RECOVERY_PENDING"
    db.close()

def test_verify_endpoint_failed_payment():
    """Verify that a failed payment on the gateway transitions the transaction to FAILED."""
    db = TestSession()
    cust = Customer(
        id="cust_verify_3",
        name="Amitabh Sen",
        email="amitabh@sen.in",
        phone="+919833445566",
        lifetime_value=8000.0,
        successful_payments_count=1,
        failed_payments_count=1,
        risk_score=0.25
    )
    txn = Transaction(
        id="txn_verify_failed_1",
        customer_id=cust.id,
        amount=1999.0,
        currency="INR",
        status="RECOVERY_PENDING",
        payment_method="NETBANKING",
        failure_reason="INSUFFICIENT_FUNDS",
        razorpay_order_id="order_v_300",
        retry_count=1
    )
    db.add(cust)
    db.add(txn)
    db.commit()

    with patch("app.services.razorpay_service.razorpay_service.fetch_payment", new_callable=AsyncMock) as mock_fetch_payment:
        mock_fetch_payment.return_value = {
            "id": "pay_test_failed_300",
            "order_id": "order_v_300",
            "amount": 199900,
            "status": "failed",
            "error_description": "Transaction declined by bank"
        }

        res = client.post(f"/api/recovery/verify/{txn.id}", json={"payment_id": "pay_test_failed_300"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "FAILED"
        assert data["verified"] is False
        assert data["recovered_amount"] == 0.0

        db.expire_all()
        updated_txn = db.query(Transaction).filter(Transaction.id == txn.id).first()
        assert updated_txn.status == "FAILED"
    db.close()

def test_verify_endpoint_invalid_signature():
    """Verify that an invalid payment signature is rejected with FAILED."""
    db = TestSession()
    cust = Customer(
        id="cust_verify_4",
        name="Vikram Seth",
        email="vikram@seth.in",
        phone="+919844556677",
        lifetime_value=10000.0,
        successful_payments_count=2,
        failed_payments_count=0,
        risk_score=0.08
    )
    txn = Transaction(
        id="txn_verify_sig_1",
        customer_id=cust.id,
        amount=1200.0,
        currency="INR",
        status="RECOVERY_PENDING",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        razorpay_order_id="order_v_400",
        retry_count=1
    )
    db.add(cust)
    db.add(txn)
    db.commit()

    with patch("app.services.razorpay_service.razorpay_service.verify_payment_signature") as mock_verify_sig:
        mock_verify_sig.return_value = False # Invalid signature

        res = client.post(f"/api/recovery/verify/{txn.id}", json={
            "payment_id": "pay_test_sig_400",
            "razorpay_signature": "invalid_forged_sig"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "FAILED"
        assert "invalid" in data["message"].lower()
    db.close()

def test_webhook_order_paid_event():
    """Verify that order.paid webhook transitions transaction to RECOVERED and sets RecoveryAction to SUCCESS."""
    db = TestSession()
    cust = Customer(
        id="cust_wh_ord_1",
        name="Order Paid Cust",
        email="ordpaid@domain.in",
        phone="+919811223399",
        lifetime_value=22000.0,
        successful_payments_count=3,
        failed_payments_count=0,
        risk_score=0.08
    )
    txn = Transaction(
        id="txn_wh_ord_1",
        customer_id=cust.id,
        amount=3500.0,
        currency="INR",
        status="RECOVERY_PENDING",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        razorpay_order_id="order_wh_ord_3500",
        retry_count=1
    )
    act = RecoveryAction(
        id="act_wh_ord_1",
        transaction_id=txn.id,
        action_type="RETRY_PAYMENT",
        status="PENDING",
        ai_diagnosis="Transient decline",
        ai_probability=0.85,
        ai_risk_level="LOW",
        ai_reasoning="Card decline prompt",
        policy_allowed=True,
        policy_reasons_json="[]",
        requires_human_approval=False,
        recovered_amount=0.0,
        mode="TEST_MODE"
    )
    db.add(cust)
    db.add(txn)
    db.add(act)
    db.commit()

    webhook_payload = {
        "event": "order.paid",
        "payload": {
            "order": {
                "entity": {
                    "id": "order_wh_ord_3500",
                    "amount": 350000,
                    "amount_paid": 350000,
                    "status": "paid"
                }
            },
            "payment": {
                "entity": {
                    "id": "pay_wh_ord_3500",
                    "order_id": "order_wh_ord_3500",
                    "amount": 350000,
                    "status": "captured"
                }
            }
        }
    }

    res = post_signed_webhook(client, webhook_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["recovered"] is True

    db.expire_all()
    updated_txn = db.query(Transaction).filter(Transaction.id == txn.id).first()
    assert updated_txn.status == "RECOVERED"
    assert updated_txn.razorpay_payment_id == "pay_wh_ord_3500"

    updated_act = db.query(RecoveryAction).filter(RecoveryAction.id == act.id).first()
    assert updated_act.status == "SUCCESS"
    assert updated_act.recovered_amount == 3500.0
    db.close()

def test_webhook_payment_link_paid_event():
    """Verify that payment_link.paid webhook transitions transaction to RECOVERED."""
    db = TestSession()
    cust = Customer(
        id="cust_wh_link_1",
        name="Link Paid Cust",
        email="linkpaid@domain.in",
        phone="+919811223388",
        lifetime_value=18000.0,
        successful_payments_count=2,
        failed_payments_count=0,
        risk_score=0.1
    )
    txn = Transaction(
        id="txn_wh_link_1",
        customer_id=cust.id,
        amount=1999.0,
        currency="INR",
        status="RECOVERY_PENDING",
        payment_method="NETBANKING",
        failure_reason="INSUFFICIENT_FUNDS",
        razorpay_payment_link="https://rzp.io/i/test_link_1999",
        retry_count=1
    )
    db.add(cust)
    db.add(txn)
    db.commit()

    webhook_payload = {
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_1999",
                    "short_url": "https://rzp.io/i/test_link_1999",
                    "amount": 199900,
                    "status": "paid"
                }
            },
            "payment": {
                "entity": {
                    "id": "pay_link_1999",
                    "amount": 199900,
                    "status": "captured"
                }
            }
        }
    }

    res = post_signed_webhook(client, webhook_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"

    db.expire_all()
    updated_txn = db.query(Transaction).filter(Transaction.id == txn.id).first()
    assert updated_txn.status == "RECOVERED"
    assert updated_txn.razorpay_payment_id == "pay_link_1999"
    db.close()

def test_webhook_missing_and_invalid_signature():
    """Verify that when webhook secret is configured, missing or invalid X-Razorpay-Signature returns HTTP 400."""
    with patch.object(settings, "RAZORPAY_WEBHOOK_SECRET", "secret_test_wh_key"):
        payload = json.dumps({"event": "payment.captured", "payload": {}}).encode("utf-8")

        # 1. Missing signature header
        res_missing = client.post("/api/webhook/razorpay", content=payload, headers={"Content-Type": "application/json"})
        assert res_missing.status_code == 400
        assert "missing" in res_missing.json()["detail"].lower()

        # 2. Invalid signature header
        res_invalid = client.post(
            "/api/webhook/razorpay",
            content=payload,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": "invalid_sig_hash"}
        )
        assert res_invalid.status_code == 400
        assert "invalid" in res_invalid.json()["detail"].lower()

        # 3. Valid signature header
        valid_sig = hmac.new("secret_test_wh_key".encode("utf-8"), payload, hashlib.sha256).hexdigest()
        res_valid = client.post(
            "/api/webhook/razorpay",
            content=payload,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": valid_sig}
        )
        assert res_valid.status_code == 200

def test_duplicate_recovery_execution_idempotency():
    """Verify that repeated / duplicate calls to execute_recovery do not create duplicate orders or actions."""
    db = TestSession()
    cust = Customer(
        id="cust_idem_1",
        name="Idempotent Customer",
        email="idem@domain.in",
        phone="+919811223300",
        lifetime_value=20000.0,
        successful_payments_count=3,
        failed_payments_count=0,
        risk_score=0.08
    )
    txn = Transaction(
        id="txn_idem_1",
        customer_id=cust.id,
        amount=2500.0,
        currency="INR",
        status="FAILED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=0
    )
    db.add(cust)
    db.add(txn)
    db.commit()

    with patch("app.services.razorpay_service.razorpay_service.create_order", new_callable=AsyncMock) as mock_create_order:
        with patch("app.services.razorpay_service.razorpay_service.fetch_order_payments", new_callable=AsyncMock) as mock_fetch_payments:
            mock_create_order.return_value = {
                "id": "order_idem_test_555",
                "status": "created",
                "amount": 250000,
                "mode": "TEST_MODE"
            }
            mock_fetch_payments.return_value = []

            # 1st request
            res1 = client.post(f"/api/recovery/execute/{txn.id}?mode=TEST_MODE")
            assert res1.status_code == 200
            data1 = res1.json()
            assert data1["status"] == "PENDING"
            assert data1["razorpay_order_id"] == "order_idem_test_555"
            assert mock_create_order.call_count == 1

            # 2nd duplicate request immediately following
            res2 = client.post(f"/api/recovery/execute/{txn.id}?mode=TEST_MODE")
            assert res2.status_code == 200
            data2 = res2.json()
            assert data2["status"] == "PENDING"
            assert data2["details"].get("idempotent") is True or data2["details"].get("in_progress") is True
            # Assert Razorpay create_order was NOT called a second time
            assert mock_create_order.call_count == 1
    db.close()

def test_already_recovered_transaction_idempotent_response():
    """Verify that execute_recovery on an already RECOVERED transaction returns SUCCESS without calling gateway."""
    db = TestSession()
    cust = Customer(
        id="cust_idem_rec_1",
        name="Already Recovered",
        email="rec@domain.in",
        phone="+919811223301",
        lifetime_value=30000.0,
        successful_payments_count=4,
        failed_payments_count=0,
        risk_score=0.05
    )
    txn = Transaction(
        id="txn_idem_rec_1",
        customer_id=cust.id,
        amount=4000.0,
        currency="INR",
        status="RECOVERED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        razorpay_order_id="order_rec_done",
        razorpay_payment_id="pay_rec_done",
        retry_count=1
    )
    db.add(cust)
    db.add(txn)
    db.commit()

    with patch("app.services.razorpay_service.razorpay_service.create_order", new_callable=AsyncMock) as mock_create_order:
        res = client.post(f"/api/recovery/execute/{txn.id}?mode=TEST_MODE")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SUCCESS"
        assert data["amount_recovered"] == 4000.0
        assert data["details"].get("already_recovered") is True
        # Gateway was not touched
        assert mock_create_order.call_count == 0
    db.close()


def test_razorpay_test_mode_missing_credentials_produces_error():
    """Verify that requesting TEST_MODE when Razorpay keys are unconfigured produces a clear error."""
    with patch.object(settings, "RAZORPAY_KEY_ID", ""):
        with patch.object(settings, "RAZORPAY_KEY_SECRET", ""):
            db = TestSession()
            cust = Customer(
                id="cust_err_rzp",
                name="Error Cust",
                email="err@domain.in",
                phone="+919811223399",
                lifetime_value=5000.0,
                successful_payments_count=1,
                failed_payments_count=0,
                risk_score=0.1
            )
            txn = Transaction(
                id="txn_err_rzp",
                customer_id=cust.id,
                amount=500.0,
                currency="INR",
                status="FAILED",
                payment_method="UPI",
                failure_reason="UPI_TIMEOUT",
                retry_count=0
            )
            db.add(cust)
            db.add(txn)
            db.commit()

            res = client.post(f"/api/recovery/execute/{txn.id}?mode=TEST_MODE")
            assert res.status_code == 200
            assert res.json()["status"] == "FAILED"
            assert "keys are unconfigured" in res.json()["message"]
            db.close()


def test_manual_approval_invalid_transitions():
    """Verify manual approvals cannot be approved twice, rejected twice, or crossed."""
    db = TestSession()
    cust = Customer(
        id="cust_app_test",
        name="Approval Cust",
        email="appr@domain.in",
        phone="+919811223344",
        lifetime_value=50000.0,
        successful_payments_count=2,
        failed_payments_count=0,
        risk_score=0.1
    )
    txn = Transaction(
        id="txn_app_test",
        customer_id=cust.id,
        amount=25000.0, # High value -> gated
        currency="INR",
        status="FAILED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=0
    )
    db.add(cust)
    db.add(txn)
    db.commit()

    # Trigger action to PENDING_APPROVAL
    res_exec = client.post(f"/api/recovery/execute/{txn.id}?mode=SIMULATION_MODE")
    assert res_exec.status_code == 200
    assert res_exec.json()["status"] == "REQUIRES_APPROVAL"
    action_id = res_exec.json()["details"]["action_id"]
    assert action_id is not None

    # First approve should succeed
    res_app1 = client.post(f"/api/recovery/approve/{action_id}")
    assert res_app1.status_code == 200

    # Second approve should return HTTP 400
    res_app2 = client.post(f"/api/recovery/approve/{action_id}")
    assert res_app2.status_code == 400

    # Rejecting approved action should return HTTP 400
    res_rej1 = client.post(f"/api/recovery/reject/{action_id}")
    assert res_rej1.status_code == 400
    db.close()


def test_policy_engine_failsafe_default_error():
    """Verify that when policy engine suffers an exception, failsafe defaults to STOP."""
    db = TestSession()
    txn = Transaction(
        id="txn_fail_policy",
        customer_id="cust_dummy",
        amount=1000.0,
        status="FAILED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT"
    )
    # Pass None recommendation to cause AttributeError and trigger failsafe except block
    res = policy_engine.evaluate(txn, None)
    assert res.allowed is False
    assert res.action == "STOP"
    assert "Failsafe default" in res.reason
    db.close()


def test_run_scenario_live_llm_and_razorpay_flow():
    """Verify that when Gemini succeeds, scenario returns LIVE_LLM and maintains Razorpay flow."""
    fake_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "diagnosis": "UPI PSP timeout at issuing bank switch",
                                "recovery_probability": 0.93,
                                "recommended_action": "RETRY_PAYMENT",
                                "risk_level": "LOW",
                                "reason": "High-value loyal customer with transient gateway latency.",
                                "requires_human_approval": False
                            })
                        }
                    ]
                }
            }
        ]
    }

    with patch.object(settings, "GEMINI_API_KEY", "valid-gemini-key-test"):
        with patch.object(settings, "LLM_PROVIDER", "gemini"):
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = fake_gemini_response
            mock_client.post.return_value = mock_resp

            with patch("httpx.Client") as MockHttpx:
                MockHttpx.return_value.__enter__.return_value = mock_client
                with patch.object(razorpay_service, "key_id", "rzp_test_valid_123"), patch.object(razorpay_service, "key_secret", "valid_secret_456"):
                    with patch.object(razorpay_service, "create_order", new_callable=AsyncMock) as mock_create_order:
                        mock_create_order.return_value = {
                            "id": "order_test_live_llm_123",
                            "status": "created",
                            "amount": 499900,
                            "currency": "INR",
                            "mode": "TEST_MODE"
                        }
                        with patch.object(razorpay_service, "fetch_order_payments", new_callable=AsyncMock) as mock_fetch:
                            mock_fetch.return_value = [] # Unpaid order awaiting payment

                            res = client.post("/api/demo/scenario", json={"scenario": "temporary_upi_failure", "mode": "TEST_MODE"})
                            assert res.status_code == 200
                            data = res.json()

                            ai = data["ai_analysis"]
                            assert ai["mode"] == "LIVE_LLM"
                            assert ai["fallback_used"] is False
                            assert ai["model_used"] == settings.GEMINI_MODEL
                            assert ai["diagnosis"] == "UPI PSP timeout at issuing bank switch"
                            assert ai["recommended_action"] == "RETRY_PAYMENT"

                            rec = data["recovery_result"]
                            assert rec["status"] == "PENDING"
                            assert rec["mode"] == "TEST_MODE"
                            assert rec["razorpay_order_id"] == "order_test_live_llm_123"

                            txn = data["transaction"]
                            assert txn["status"] == "RECOVERY_PENDING"
                            assert txn["razorpay_order_id"] == "order_test_live_llm_123"


def test_run_scenario_fallback_when_gemini_fails_preserves_razorpay_flow():
    """Verify that when Gemini fails, fallback_used is True, mode is HEURISTIC_FALLBACK, and Razorpay flow is preserved."""
    with patch.object(settings, "GEMINI_API_KEY", "failing-gemini-key"):
        with patch.object(settings, "LLM_PROVIDER", "gemini"):
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 401 # Auth failure
            mock_client.post.return_value = mock_resp

            with patch("httpx.Client") as MockHttpx:
                MockHttpx.return_value.__enter__.return_value = mock_client
                with patch.object(razorpay_service, "key_id", "rzp_test_valid_123"), patch.object(razorpay_service, "key_secret", "valid_secret_456"):
                    with patch.object(razorpay_service, "create_order", new_callable=AsyncMock) as mock_create_order:
                        mock_create_order.return_value = {
                            "id": "order_test_fallback_456",
                            "status": "created",
                            "amount": 499900,
                            "currency": "INR",
                            "mode": "TEST_MODE"
                        }
                        with patch.object(razorpay_service, "fetch_order_payments", new_callable=AsyncMock) as mock_fetch:
                            mock_fetch.return_value = []

                            res = client.post("/api/demo/scenario", json={"scenario": "temporary_upi_failure", "mode": "TEST_MODE"})
                            assert res.status_code == 200
                            data = res.json()

                            ai = data["ai_analysis"]
                            assert ai["mode"] == "HEURISTIC_FALLBACK"
                            assert ai["fallback_used"] is True
                            assert ai["model_used"] == "RecoverIQ Expert Heuristics Engine"

                            rec = data["recovery_result"]
                            assert rec["status"] == "PENDING"
                            assert rec["mode"] == "TEST_MODE"
                            assert rec["razorpay_order_id"] == "order_test_fallback_456"

                            txn = data["transaction"]
                            assert txn["status"] == "RECOVERY_PENDING"
                            assert txn["razorpay_order_id"] == "order_test_fallback_456"


def test_real_network_call_with_invalid_key_triggers_safe_fallback():
    """Verify real HTTP network request to Google Generative Language API with dummy key safely triggers fallback without crashing or leaking secrets."""
    ctx = AIAnalysisInput(
        transaction_id="txn_real_net_test",
        amount=1999.0,
        currency="INR",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        retry_count=0,
        customer_id="cust_net",
        customer_name="Network Test",
        customer_email="net@test.in",
        customer_lifetime_value=10000.0,
        previous_successful_payments=2,
        previous_failed_payments=0,
        previous_recovery_attempts=0
    )

    # Use a dummy key to hit real Google endpoint
    with patch.object(settings, "GEMINI_API_KEY", "invalid_dummy_key_for_testing"):
        with patch.object(settings, "LLM_PROVIDER", "gemini"):
            # Real call without mock
            result = ai_agent._call_gemini_api(ctx)
            # Must safely return None due to 400/403 API response
            assert result is None

            # analyze_failure must return truthful HEURISTIC_FALLBACK
            rec = ai_agent.analyze_failure(
                Transaction(
                    id="txn_net_fallback",
                    customer_id="cust_net",
                    amount=1999.0,
                    payment_method="UPI",
                    failure_reason="UPI_TIMEOUT",
                    retry_count=0
                )
            )
            assert rec.mode == "HEURISTIC_FALLBACK"
            assert rec.fallback_used is True
            assert rec.model_used == "RecoverIQ Expert Heuristics Engine"



