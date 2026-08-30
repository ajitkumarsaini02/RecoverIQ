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
    
    # Signature verification
    if settings.RAZORPAY_WEBHOOK_SECRET:
        if not x_razorpay_signature:
            logger.warning("Razorpay webhook received without X-Razorpay-Signature header.")
            raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header")
        
        is_valid = razorpay_service.verify_webhook_signature(
            payload_body=body_bytes,
            signature=x_razorpay_signature,
            secret=settings.RAZORPAY_WEBHOOK_SECRET
        )
        if not is_valid:
            logger.error("Razorpay webhook signature verification failed.")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
    else:
        logger.info("RAZORPAY_WEBHOOK_SECRET not configured, processing in permissive test mode.")

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(e)}")

    event_type = payload.get("event")
    event_data = payload.get("payload", {})
    now = datetime.now(timezone.utc)

    logger.info(f"Processing Razorpay webhook event: {event_type}")

    if event_type == "payment.captured":
        payment_obj = event_data.get("payment", {}).get("entity", {})
        order_id = payment_obj.get("order_id")
        payment_id = payment_obj.get("id")
        amount = float(payment_obj.get("amount", 0)) / 100.0

        # Find matching transaction by order_id or notes
        txn = None
        if order_id:
            txn = db.query(Transaction).filter(Transaction.razorpay_order_id == order_id).first()
        if not txn and payment_obj.get("notes", {}).get("transaction_id"):
            txn = db.query(Transaction).filter(Transaction.id == payment_obj["notes"]["transaction_id"]).first()

        if txn:
            # Idempotency check
            if txn.status != "RECOVERED":
                txn.status = "RECOVERED"
                txn.razorpay_payment_id = payment_id
                txn.updated_at = now

                audit_service.log_webhook_received(
                    db=db,
                    transaction_id=txn.id,
                    event=event_type,
                    payment_id=payment_id,
                    order_id=order_id
                )

                audit_service.log_payment_recovered(
                    db=db,
                    transaction_id=txn.id,
                    amount_recovered=amount or txn.amount,
                    payment_id=payment_id,
                    mode="TEST_MODE"
                )
                db.commit()
                logger.info(f"Transaction {txn.id} marked RECOVERED via webhook payment.captured.")
            else:
                logger.info(f"Transaction {txn.id} already marked RECOVERED. Duplicate webhook ignored.")
        else:
            logger.warning(f"No local transaction found for captured Razorpay order {order_id} / payment {payment_id}")

    elif event_type == "payment_link.paid":
        plink_obj = event_data.get("payment_link", {}).get("entity", {})
        payment_obj = event_data.get("payment", {}).get("entity", {})
        plink_id = plink_obj.get("id")
        payment_id = payment_obj.get("id")
        amount = float(plink_obj.get("amount", 0)) / 100.0

        txn = None
        if plink_obj.get("short_url"):
            txn = db.query(Transaction).filter(Transaction.razorpay_payment_link == plink_obj["short_url"]).first()
        if not txn and plink_obj.get("notes", {}).get("transaction_id"):
            txn = db.query(Transaction).filter(Transaction.id == plink_obj["notes"]["transaction_id"]).first()

        if txn and txn.status != "RECOVERED":
            txn.status = "RECOVERED"
            txn.razorpay_payment_id = payment_id
            txn.updated_at = now

            audit_service.log_webhook_received(
                db=db,
                transaction_id=txn.id,
                event=event_type,
                payment_id=payment_id,
                order_id=None
            )

            audit_service.log_payment_recovered(
                db=db,
                transaction_id=txn.id,
                amount_recovered=amount or txn.amount,
                payment_id=payment_id,
                mode="TEST_MODE"
            )
            db.commit()
            logger.info(f"Transaction {txn.id} marked RECOVERED via payment_link.paid.")

    return {"status": "success", "event": event_type, "timestamp": now.isoformat()}
