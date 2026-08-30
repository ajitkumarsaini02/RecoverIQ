import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.services.ai_agent import ai_agent, AIAgentRecommendation
from app.db.models import Transaction, Customer

def test_pydantic_schema_validation():
    # Valid schema test
    valid_rec = AIAgentRecommendation(
        diagnosis="Temporary UPI timeout",
        recovery_probability=0.91,
        recommended_action="RETRY_PAYMENT",
        risk_level="LOW",
        reason="Customer has strong payment history",
        requires_human_approval=False,
        mode="DEMO_FALLBACK",
        model_used="RecoverIQ Expert Engine",
        fallback_used=True
    )
    assert valid_rec.recovery_probability == 0.91
    assert valid_rec.recommended_action == "RETRY_PAYMENT"
    assert valid_rec.risk_level == "LOW"

    # Test invalid probability (> 1.0)
    with pytest.raises(ValidationError):
        AIAgentRecommendation(
            diagnosis="Error",
            recovery_probability=1.5,
            recommended_action="RETRY_PAYMENT",
            risk_level="LOW",
            reason="Test",
            requires_human_approval=False
        )

    # Test invalid action
    with pytest.raises(ValidationError):
        AIAgentRecommendation(
            diagnosis="Error",
            recovery_probability=0.8,
            recommended_action="INVALID_ACTION_NAME",
            risk_level="LOW",
            reason="Test",
            requires_human_approval=False
        )

def test_ai_agent_upi_timeout_diagnosis():
    cust = Customer(
        id="cust_upi_1",
        name="Priya Sharma",
        email="priya@gmail.com",
        phone="+919876543210",
        lifetime_value=39992.0,
        successful_payments_count=8,
        failed_payments_count=1,
        risk_score=0.08
    )
    txn = Transaction(
        id="txn_upi_1",
        customer_id=cust.id,
        amount=4999.0,
        currency="INR",
        status="FAILED",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        customer_lifetime_value=39992.0,
        previous_successful_payments=8,
        previous_failed_payments=1,
        retry_count=0
    )

    rec = ai_agent.analyze_failure(transaction=txn, customer=cust)
    assert rec.diagnosis == "Temporary UPI PSP timeout or NPCI network latency"
    assert rec.recovery_probability == 0.91
    assert rec.recommended_action == "RETRY_PAYMENT"
    assert rec.risk_level == "LOW"
    assert "Priya Sharma" in rec.reason
    assert rec.requires_human_approval is False
    assert rec.mode in ["HEURISTIC_FALLBACK", "DEMO_FALLBACK"]

def test_ai_agent_bank_decline_diagnosis():
    cust = Customer(
        id="cust_card_1",
        name="Rahul Verma",
        email="rahul@corp.in",
        phone="+919845190123",
        lifetime_value=14994.0,
        successful_payments_count=6,
        failed_payments_count=2,
        risk_score=0.22
    )
    txn = Transaction(
        id="txn_card_1",
        customer_id=cust.id,
        amount=2499.0,
        currency="INR",
        status="FAILED",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        customer_lifetime_value=14994.0,
        previous_successful_payments=6,
        previous_failed_payments=2,
        retry_count=0
    )

    rec = ai_agent.analyze_failure(transaction=txn, customer=cust)
    assert "Bank issuer decline" in rec.diagnosis
    assert rec.recommended_action == "ALTERNATIVE_PAYMENT_METHOD"
    assert rec.risk_level == "MEDIUM"

def test_ai_agent_insufficient_funds_diagnosis():
    txn = Transaction(
        id="txn_funds_1",
        customer_id="cust_funds_1",
        amount=14999.0,
        currency="INR",
        status="FAILED",
        payment_method="NETBANKING",
        failure_reason="INSUFFICIENT_FUNDS",
        retry_count=0
    )
    rec = ai_agent.analyze_failure(transaction=txn)
    assert "Insufficient account balance" in rec.diagnosis
    assert rec.recommended_action == "PAYMENT_LINK"
    assert rec.recovery_probability == 0.55

def test_ai_agent_repeated_failure_stop():
    txn = Transaction(
        id="txn_stop_1",
        customer_id="cust_stop_1",
        amount=4999.0,
        currency="INR",
        status="FAILED",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        retry_count=2, # Cap reached
        max_retries=2
    )
    rec = ai_agent.analyze_failure(transaction=txn)
    assert rec.recommended_action == "STOP"
    assert rec.risk_level == "HIGH"
    assert rec.recovery_probability < 0.25

def test_ai_agent_high_value_human_approval():
    txn = Transaction(
        id="txn_hv_1",
        customer_id="cust_hv_1",
        amount=49999.0, # High value
        currency="INR",
        status="FAILED",
        payment_method="CARD",
        failure_reason="BANK_DECLINED",
        retry_count=0
    )
    rec = ai_agent.analyze_failure(transaction=txn)
    assert rec.requires_human_approval is True
    assert rec.recommended_action in ["HUMAN_ESCALATION", "PAYMENT_LINK"]

def test_api_agent_analyze_endpoint():
    client = TestClient(app)
    # First get a transaction
    res = client.get("/api/transactions?limit=1")
    assert res.status_code == 200
    txn_id = res.json()["items"][0]["id"]

    # Run AI analysis
    analyze_res = client.post(f"/api/agent/analyze/{txn_id}")
    assert analyze_res.status_code == 200
    data = analyze_res.json()
    assert data["transaction_id"] == txn_id
    assert "ai_recommendation" in data
    assert "policy_decision" in data
    
    rec = data["ai_recommendation"]
    assert "diagnosis" in rec
    assert "recovery_probability" in rec
    assert "recommended_action" in rec
    assert "risk_level" in rec
    assert "reason" in rec
    assert "requires_human_approval" in rec
    assert rec["mode"] in ["HEURISTIC_FALLBACK", "DEMO_FALLBACK", "GEMINI"]

def test_gemini_mocked_success_response():
    from unittest.mock import patch, MagicMock
    import json
    import httpx
    from app.config import settings
    from app.services.ai_agent import AIAnalysisInput

    ctx = AIAnalysisInput(
        transaction_id="txn_gemini_mock_1",
        amount=1999.0,
        currency="INR",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        error_code="PSP_TIMEOUT",
        retry_count=0,
        customer_id="cust_g1",
        customer_name="Aarav Sharma",
        customer_email="aarav@gmail.com",
        customer_lifetime_value=25000.0,
        previous_successful_payments=4,
        previous_failed_payments=0,
        previous_recovery_attempts=0
    )

    fake_resp_body = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "diagnosis": "UPI PSP timeout at issuing bank switch",
                                "recovery_probability": 0.92,
                                "recommended_action": "RETRY_PAYMENT",
                                "risk_level": "LOW",
                                "reason": "Customer has pristine payment history.",
                                "requires_human_approval": False
                            })
                        }
                    ]
                }
            }
        ]
    }

    with patch.object(settings, "GEMINI_API_KEY", "valid_gemini_test_key"):
        with patch.object(settings, "LLM_PROVIDER", "gemini"):
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = fake_resp_body
            mock_client.post.return_value = mock_resp

            with patch("httpx.Client") as MockClient:
                MockClient.return_value.__enter__.return_value = mock_client
                rec = ai_agent._call_gemini_api(ctx)

                assert rec is not None
                assert rec.diagnosis == "UPI PSP timeout at issuing bank switch"
                assert rec.recovery_probability == 0.92
                assert rec.recommended_action == "RETRY_PAYMENT"
                assert rec.risk_level == "LOW"
                assert rec.mode == "GEMINI"
                assert rec.fallback_used is False
                assert "Gemini" in rec.model_used

def test_gemini_timeout_and_error_fallback():
    from unittest.mock import patch, MagicMock
    import httpx
    from app.config import settings
    from app.services.ai_agent import AIAnalysisInput

    ctx = AIAnalysisInput(
        transaction_id="txn_gemini_timeout",
        amount=1999.0,
        currency="INR",
        payment_method="UPI",
        failure_reason="UPI_TIMEOUT",
        error_code="PSP_TIMEOUT",
        retry_count=0,
        customer_id="cust_g2",
        customer_name="Pooja Verma",
        customer_email="pooja@gmail.com",
        customer_lifetime_value=15000.0,
        previous_successful_payments=2,
        previous_failed_payments=0,
        previous_recovery_attempts=0
    )

    with patch.object(settings, "GEMINI_API_KEY", "valid_gemini_test_key"):
        with patch.object(settings, "LLM_PROVIDER", "gemini"):
            mock_client = MagicMock()
            mock_client.post.side_effect = httpx.TimeoutException("Read timeout from Gemini endpoint")

            with patch("httpx.Client") as MockClient:
                MockClient.return_value.__enter__.return_value = mock_client
                rec = ai_agent._call_gemini_api(ctx)
                assert rec is None # Safely returns None to trigger heuristic fallback
