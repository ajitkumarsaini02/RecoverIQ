import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.db.models import Transaction, RecoveryAction, AuditEvent
from app.services.razorpay_service import razorpay_service
from app.services.audit_service import audit_service
from app.config import settings

logger = logging.getLogger("recoveriq.webhook")
router = APIRouter(prefix="/api/webhook", tags=["Webhooks"])

@router.post("/razorpay")
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Receives and independently verifies live Razorpay Webhooks.
    Handles 'payment.captured', 'payment.failed', and 'payment_link.paid'.
    """
    body_bytes = await request.body()
    
    # Unconditional Signature verification
    if not x_razorpay_signature:
        logger.warning("Razorpay webhook received without X-Razorpay-Signature header.")
        raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header")
    
    # In production a real webhook secret is mandatory — never verify against the
    # public default ("whsec_dummy" ships in source). Fail closed so a forged webhook
    # cannot fabricate a recovery. Local/test/demo runs may fall back to the default.
    webhook_secret = (settings.RAZORPAY_WEBHOOK_SECRET or "").strip()
    if settings.ENVIRONMENT == "production":
        if not webhook_secret or webhook_secret == "whsec_dummy":
            logger.error("Webhook rejected: RAZORPAY_WEBHOOK_SECRET is not configured (or is the insecure default) in production.")
            raise HTTPException(status_code=503, detail="Webhook signature secret is not configured")
    elif not webhook_secret:
        webhook_secret = "whsec_dummy"
    is_valid = razorpay_service.verify_webhook_signature(
        payload_body=body_bytes,
        signature=x_razorpay_signature,
        secret=webhook_secret
    )
    if not is_valid:
        logger.error("Razorpay webhook signature verification failed.")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(e)}")

    event_type = payload.get("event")
    event_data = payload.get("payload", {})
    now = datetime.now(timezone.utc)

    logger.info(f"Processing Razorpay webhook event: {event_type}")

    if event_type in ["payment.captured", "order.paid"]:
        payment_obj = event_data.get("payment", {}).get("entity", {})
        order_obj = event_data.get("order", {}).get("entity", {})

        order_id = payment_obj.get("order_id") or order_obj.get("id")
        payment_id = payment_obj.get("id")
        amount = float(payment_obj.get("amount", 0) or order_obj.get("amount_paid", 0) or order_obj.get("amount", 0)) / 100.0

        # Find matching transaction by order_id or notes with database locking where supported (PostgreSQL)
        txn_query = db.query(Transaction)
        if db.bind.dialect.name == "postgresql":
            txn_query = txn_query.with_for_update()

        txn = None
        if order_id:
            txn = txn_query.filter(Transaction.razorpay_order_id == order_id).first()
        if not txn and payment_obj.get("notes", {}).get("transaction_id"):
            txn = txn_query.filter(Transaction.id == payment_obj["notes"]["transaction_id"]).first()
        if not txn and order_obj.get("notes", {}).get("transaction_id"):
            txn = txn_query.filter(Transaction.id == order_obj["notes"]["transaction_id"]).first()

        if txn:
            # Idempotency check: only recover if not already recovered
            if txn.status != "RECOVERED":
                txn.status = "RECOVERED"
                if payment_id:
                    txn.razorpay_payment_id = payment_id
                txn.updated_at = now

                # Update recent recovery action
                act = db.query(RecoveryAction).filter(RecoveryAction.transaction_id == txn.id).order_by(RecoveryAction.created_at.desc()).first()
                if act and act.status != "SUCCESS":
                    act.status = "SUCCESS"
                    act.recovered_amount = txn.amount
                    act.executed_at = now

                audit_service.log_webhook_received(
                    db=db,
                    transaction_id=txn.id,
                    event=event_type,
                    payment_id=payment_id,
                    order_id=order_id
                )

                mode = act.mode if act else "TEST_MODE"
                audit_service.log_payment_recovered(
                    db=db,
                    transaction_id=txn.id,
                    amount_recovered=amount or txn.amount,
                    payment_id=payment_id,
                    mode=mode
                )
                db.commit()
                logger.info(f"Transaction {txn.id} marked RECOVERED via webhook {event_type}.")
                return {"status": "success", "event": event_type, "transaction_id": txn.id, "recovered": True}
            else:
                logger.info(f"Transaction {txn.id} already marked RECOVERED. Duplicate webhook ignored.")
                return {"status": "ignored", "event": event_type, "transaction_id": txn.id, "reason": "Already recovered"}
        else:
            logger.warning(f"No local transaction found for Razorpay order {order_id} / payment {payment_id}")
            return {"status": "ignored", "event": event_type, "reason": "Transaction not found"}

    elif event_type == "payment_link.paid":
        plink_obj = event_data.get("payment_link", {}).get("entity", {})
        payment_obj = event_data.get("payment", {}).get("entity", {})
        plink_id = plink_obj.get("id")
        payment_id = payment_obj.get("id")
        amount = float(plink_obj.get("amount", 0)) / 100.0

        # Find matching transaction by short_url or notes with database locking where supported (PostgreSQL)
        txn_query = db.query(Transaction)
        if db.bind.dialect.name == "postgresql":
            txn_query = txn_query.with_for_update()

        txn = None
        if plink_obj.get("short_url"):
            txn = txn_query.filter(Transaction.razorpay_payment_link == plink_obj["short_url"]).first()
        if not txn and plink_id:
            txn = txn_query.filter(Transaction.razorpay_payment_link.contains(plink_id)).first()
        if not txn and plink_obj.get("notes", {}).get("transaction_id"):
            txn = txn_query.filter(Transaction.id == plink_obj["notes"]["transaction_id"]).first()

        if txn:
            if txn.status != "RECOVERED":
                txn.status = "RECOVERED"
                if payment_id:
                    txn.razorpay_payment_id = payment_id
                txn.updated_at = now

                # Update recent recovery action
                act = db.query(RecoveryAction).filter(RecoveryAction.transaction_id == txn.id).order_by(RecoveryAction.created_at.desc()).first()
                if act and act.status != "SUCCESS":
                    act.status = "SUCCESS"
                    act.recovered_amount = txn.amount
                    act.executed_at = now

                audit_service.log_webhook_received(
                    db=db,
                    transaction_id=txn.id,
                    event=event_type,
                    payment_id=payment_id,
                    order_id=None
                )

                mode = act.mode if act else "TEST_MODE"
                audit_service.log_payment_recovered(
                    db=db,
                    transaction_id=txn.id,
                    amount_recovered=amount or txn.amount,
                    payment_id=payment_id,
                    mode=mode
                )
                db.commit()
                logger.info(f"Transaction {txn.id} marked RECOVERED via payment_link.paid.")
                return {"status": "success", "event": event_type, "transaction_id": txn.id, "recovered": True}
            else:
                logger.info(f"Transaction {txn.id} already marked RECOVERED. Duplicate webhook ignored.")
                return {"status": "ignored", "event": event_type, "transaction_id": txn.id, "reason": "Already recovered"}
        else:
            logger.warning(f"No local transaction found for payment link {plink_id}")
            return {"status": "ignored", "event": event_type, "reason": "Transaction not found"}

    return {"status": "success", "event": event_type, "timestamp": now.isoformat()}
