import random
import uuid
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.db.models import Customer, Transaction, RecoveryAction, AuditEvent, Base
from app.db.session import engine

FIRST_NAMES = [
    "Aarav", "Aditi", "Advait", "Akshay", "Ananya", "Anika", "Arjun", "Aryan", "Bhavya", 
    "Chetan", "Deepak", "Dev", "Divya", "Gaurav", "Harsh", "Ishaan", "Janhavi", "Kabir", 
    "Kavya", "Karan", "Kunal", "Manish", "Meera", "Neha", "Nikhil", "Pooja", "Pranav", 
    "Priya", "Rahul", "Rhea", "Rohan", "Roshni", "Sakshi", "Sameer", "Sanjay", "Siddharth", 
    "Sneha", "Tanvi", "Tarun", "Varun", "Vikram", "Yash", "Zoya", "Ravi", "Suresh", "Manoj"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Gupta", "Nair", "Singh", "Reddy", "Iyer", "Mehta", "Chopra",
    "Mukherjee", "Banerjee", "Bhatia", "Joshi", "Deshmukh", "Kulkarni", "Aggarwal", "Mishra",
    "Dubey", "Kapoor", "Malhotra", "Saxena", "Sen", "Pillai", "Choudhury", "Bose", "Trivedi"
]

DOMAINS = ["gmail.com", "outlook.com", "yahoo.in", "icloud.com", "corporate.in", "enterprise.co"]

INDIAN_AMOUNTS = [
    499.0, 999.0, 1499.0, 1999.0, 2499.0, 3999.0, 4999.0, 7499.0, 9999.0, 
    14999.0, 19999.0, 24999.0, 49999.0, 99999.0
]

PAYMENT_METHODS = ["UPI", "CARD", "NETBANKING", "WALLET"]
PAYMENT_METHOD_WEIGHTS = [0.60, 0.25, 0.10, 0.05]

FAILURE_REASONS = [
    "UPI_TIMEOUT",
    "BANK_DECLINED",
    "INSUFFICIENT_FUNDS",
    "NETWORK_ERROR",
    "PAYMENT_METHOD_ERROR",
    "UNKNOWN"
]
FAILURE_REASON_WEIGHTS = [0.35, 0.25, 0.15, 0.12, 0.08, 0.05]

ERROR_CODES = {
    "UPI_TIMEOUT": ["PSP_TIMEOUT", "VPA_DEBIT_TIMEOUT", "NPCI_LATENCY"],
    "BANK_DECLINED": ["ISSUER_DECLINE", "CARD_RESTRICTED", "AUTHENTICATION_FAILED"],
    "INSUFFICIENT_FUNDS": ["INSUFFICIENT_BALANCE", "LIMIT_EXCEEDED"],
    "NETWORK_ERROR": ["GATEWAY_TIMEOUT", "CONNECTION_RESET", "SSL_HANDSHAKE_ERROR"],
    "PAYMENT_METHOD_ERROR": ["INVALID_CARD_NUMBER", "EXPIRED_CARD", "VPA_NOT_FOUND"],
    "UNKNOWN": ["GENERIC_PAYMENT_ERROR", "INTERNAL_GATEWAY_ERROR"]
}

def generate_indian_phone():
    return f"+91 {random.randint(6, 9)}{random.randint(100000000, 999999999)}"

def seed_database(db: Session, customer_count: int = 350, transaction_count: int = 1200, force_reseed: bool = False):
    """
    Generates 300+ customers and 1,000+ transactions with realistic Indian merchant payment attributes.
    """
    # Create tables if not present
    Base.metadata.create_all(bind=db.get_bind())

    existing_txns = db.query(Transaction).count()
    if existing_txns >= 1000 and not force_reseed:
        return {
            "message": "Database already seeded with synthetic merchant data",
            "customers_count": db.query(Customer).count(),
            "transactions_count": existing_txns,
            "status": "SKIPPED"
        }

    if force_reseed:
        # Clear existing data
        db.query(AuditEvent).delete()
        db.query(RecoveryAction).delete()
        db.query(Transaction).delete()
        db.query(Customer).delete()
        db.commit()

    random.seed(42) # Deterministic realism
    now = datetime.now(timezone.utc)

    # 1. Generate Customers
    customers = []
    for i in range(1, customer_count + 1):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}{random.randint(10, 999)}@{random.choice(DOMAINS)}"
        phone = generate_indian_phone()
        
        # Payment history profile
        successful_cnt = random.choices([0, 1, 2, 4, 8, 15, 25], weights=[0.05, 0.15, 0.25, 0.30, 0.15, 0.08, 0.02])[0]
        failed_cnt = random.choices([0, 1, 2, 3, 5], weights=[0.40, 0.35, 0.15, 0.07, 0.03])[0]
        
        avg_basket = random.choice([999.0, 2499.0, 4999.0, 9999.0, 15000.0])
        ltv = successful_cnt * avg_basket
        risk_score = round(min(0.95, max(0.05, (failed_cnt * 0.20) / (successful_cnt + 1) + random.uniform(0.02, 0.15))), 2)

        created_days_ago = random.randint(10, 180)
        cust_created = now - timedelta(days=created_days_ago)

        cust = Customer(
            id=f"cust_{i:04d}",
            name=name,
            email=email,
            phone=phone,
            lifetime_value=ltv,
            successful_payments_count=successful_cnt,
            failed_payments_count=failed_cnt,
            risk_score=risk_score,
            created_at=cust_created,
            updated_at=cust_created
        )
        customers.append(cust)
        db.add(cust)

    db.flush()

    # 2. Generate Transactions
    transactions = []
    audit_events = []
    recovery_actions = []

    for i in range(1, transaction_count + 1):
        customer = random.choice(customers)
        amount = random.choice(INDIAN_AMOUNTS)
        payment_method = random.choices(PAYMENT_METHODS, weights=PAYMENT_METHOD_WEIGHTS)[0]
        failure_reason = random.choices(FAILURE_REASONS, weights=FAILURE_REASON_WEIGHTS)[0]
        error_code = random.choice(ERROR_CODES[failure_reason])

        # Timeline spread over last 30 days
        minutes_ago = random.randint(5, 30 * 24 * 60)
        txn_time = now - timedelta(minutes=minutes_ago)

        # Realistic recovery status distribution
        # 60% FAILED (ready for recovery), 15% RECOVERED, 10% APPROVAL_REQUIRED, 10% STOPPED, 5% RECOVERY_PENDING
        status = random.choices(
            ["FAILED", "RECOVERED", "APPROVAL_REQUIRED", "STOPPED", "RECOVERY_PENDING"],
            weights=[0.60, 0.18, 0.10, 0.08, 0.04]
        )[0]

        retry_count = 0
        if status == "RECOVERED":
            retry_count = random.choice([1, 2])
        elif status == "STOPPED":
            retry_count = random.choice([2, 3])
        elif status in ["FAILED", "RECOVERY_PENDING", "APPROVAL_REQUIRED"]:
            retry_count = random.choice([0, 1])

        txn = Transaction(
            id=f"txn_{i:05d}",
            customer_id=customer.id,
            amount=amount,
            currency="INR",
            status=status,
            payment_method=payment_method,
            failure_reason=failure_reason,
            error_code=error_code,
            customer_lifetime_value=customer.lifetime_value,
            previous_successful_payments=customer.successful_payments_count,
            previous_failed_payments=customer.failed_payments_count,
            previous_recovery_attempts=retry_count,
            retry_count=retry_count,
            max_retries=2,
            last_recovery_attempt_at=txn_time + timedelta(minutes=2) if retry_count > 0 else None,
            razorpay_order_id=f"order_test_{uuid.uuid4().hex[:14]}",
            razorpay_payment_id=f"pay_test_{uuid.uuid4().hex[:14]}",
            created_at=txn_time,
            updated_at=txn_time
        )
        transactions.append(txn)
        db.add(txn)

        # Create Initial Payment Failure Audit Event
        aud_fail = AuditEvent(
            id=f"aud_{uuid.uuid4().hex[:12]}",
            timestamp=txn_time,
            transaction_id=txn.id,
            event_type="PAYMENT_FAILED_DETECTED",
            actor="RAZORPAY_GATEWAY",
            decision="FAILURE_RECORDED",
            details_json=json.dumps({
                "amount": amount,
                "currency": "INR",
                "failure_reason": failure_reason,
                "error_code": error_code,
                "payment_method": payment_method,
                "mode": "TEST_MODE"
            })
        )
        audit_events.append(aud_fail)
        db.add(aud_fail)

        # For RECOVERED transactions, create recovery action and success audit trail
        if status == "RECOVERED":
            action = RecoveryAction(
                id=f"act_{uuid.uuid4().hex[:12]}",
                transaction_id=txn.id,
                action_type="RETRY_PAYMENT" if payment_method == "UPI" else "PAYMENT_LINK",
                status="SUCCESS",
                ai_diagnosis=f"Recovered from {failure_reason} with high customer confidence",
                ai_probability=round(random.uniform(0.78, 0.95), 2),
                ai_risk_level="LOW",
                ai_reasoning=f"High customer lifetime value (₹{customer.lifetime_value:,.0f}) and clean payment track record.",
                policy_allowed=True,
                policy_reasons_json=json.dumps(["Policy Rule #1: Within 2 retry limit", "Policy Rule #2: Low risk threshold satisfied"]),
                requires_human_approval=False,
                recovered_amount=amount,
                execution_details_json=json.dumps({"gateway": "Razorpay Test Mode", "attempt": retry_count, "payment_status": "captured"}),
                mode="TEST_MODE",
                created_at=txn_time + timedelta(minutes=1),
                executed_at=txn_time + timedelta(minutes=2)
            )
            recovery_actions.append(action)
            db.add(action)

            aud_recov = AuditEvent(
                id=f"aud_{uuid.uuid4().hex[:12]}",
                timestamp=txn_time + timedelta(minutes=2),
                transaction_id=txn.id,
                event_type="PAYMENT_RECOVERED",
                actor="AI_AGENT",
                decision="REVENUE_RECOVERED",
                details_json=json.dumps({
                    "recovered_amount": amount,
                    "action_type": action.action_type,
                    "recovery_probability": action.ai_probability,
                    "mode": "TEST_MODE"
                })
            )
            audit_events.append(aud_recov)
            db.add(aud_recov)

    db.commit()

    return {
        "message": "Successfully seeded synthetic merchant dataset",
        "customers_created": len(customers),
        "transactions_created": len(transactions),
        "audit_events_created": len(audit_events),
        "status": "SUCCESS"
    }
