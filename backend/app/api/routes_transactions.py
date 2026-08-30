from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc
from typing import Optional, List
from app.db.session import get_db
from app.db.models import Transaction, Customer, RecoveryAction, AuditEvent
from app.schemas.transaction import TransactionSchema, TransactionListResponse, CustomerSchema
from app.services.seed_service import seed_database

router = APIRouter(prefix="/api", tags=["Transactions & Seed"])

@router.post("/seed")
def seed_data(force: bool = False, db: Session = Depends(get_db)):
    """Seed the database with 300+ customers and 1,000+ realistic synthetic transactions."""
    result = seed_database(db=db, force_reseed=force)
    return result

@router.get("/transactions", response_model=TransactionListResponse)
def list_transactions(
    status: Optional[str] = Query(None, description="Filter by status (FAILED, RECOVERED, APPROVAL_REQUIRED, STOPPED, etc.)"),
    failure_reason: Optional[str] = Query(None, description="Filter by failure reason (UPI_TIMEOUT, BANK_DECLINED, etc.)"),
    payment_method: Optional[str] = Query(None, description="Filter by payment method (UPI, CARD, NETBANKING, WALLET)"),
    search: Optional[str] = Query(None, description="Search by transaction ID, customer name or email"),
    limit: int = Query(25, ge=1, le=200, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """Retrieve paginated transactions with flexible filtering."""
    query = db.query(Transaction).options(joinedload(Transaction.customer))

    if status and status != "ALL":
        query = query.filter(Transaction.status == status)

    if failure_reason and failure_reason != "ALL":
        query = query.filter(Transaction.failure_reason == failure_reason)

    if payment_method and payment_method != "ALL":
        query = query.filter(Transaction.payment_method == payment_method)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.join(Transaction.customer).filter(
            or_(
                Transaction.id.ilike(search_pattern),
                Customer.name.ilike(search_pattern),
                Customer.email.ilike(search_pattern),
                Transaction.error_code.ilike(search_pattern)
            )
        )

    total = query.count()
    transactions = query.order_by(desc(Transaction.created_at)).offset(offset).limit(limit).all()

    items = []
    for txn in transactions:
        d = txn.to_dict(include_relations=True)
        items.append(TransactionSchema(**d))

    page = (offset // limit) + 1
    total_pages = (total + limit - 1) // limit if limit > 0 else 1

    return TransactionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=limit,
        total_pages=total_pages,
        data_label="DEMO / SYNTHETIC DATA"
    )

@router.get("/transactions/{transaction_id}", response_model=TransactionSchema)
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    """Fetch complete transaction details with customer history, recovery actions, and audit trail."""
    txn = db.query(Transaction).options(
        joinedload(Transaction.customer),
        joinedload(Transaction.recovery_actions),
        joinedload(Transaction.audit_events)
    ).filter(Transaction.id == transaction_id).first()

    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction with ID '{transaction_id}' not found.")

    data = txn.to_dict(include_relations=True)
    data["recovery_actions"] = [act.to_dict() for act in txn.recovery_actions]
    data["audit_events"] = [aud.to_dict() for aud in txn.audit_events]

    return TransactionSchema(**data)

@router.get("/customers", response_model=List[CustomerSchema])
def list_customers(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Retrieve customers with pagination and optional search."""
    query = db.query(Customer)
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Customer.name.ilike(search_pattern),
                Customer.email.ilike(search_pattern),
                Customer.id.ilike(search_pattern)
            )
        )
    customers = query.order_by(desc(Customer.created_at)).offset(offset).limit(limit).all()
    return [CustomerSchema(**c.to_dict()) for c in customers]

@router.get("/customers/{customer_id}", response_model=CustomerSchema)
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    """Fetch single customer by ID."""
    cust = db.query(Customer).filter(Customer.id == customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail=f"Customer with ID '{customer_id}' not found.")
    return CustomerSchema(**cust.to_dict())

