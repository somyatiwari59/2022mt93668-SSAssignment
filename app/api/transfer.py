# app/api/transfer.py
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import uuid

from app.db.session import SessionLocal

router = APIRouter(tags=["transfer"])


# ------- DB Session dependency -------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------- Request Schema -------
class TransferIn(BaseModel):
    source_account_id: uuid.UUID
    dest_account_id: uuid.UUID
    amount: float = Field(gt=0)
    reference: Optional[str] = None


# ------- Endpoint -------
@router.post("/transfer", status_code=201)
def transfer(
    payload: TransferIn,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(None),
):
    """
    Skeleton Transfer Endpoint:
    - Validates input
    - Uses idempotency_key placeholder
    - You will fill business logic later
    """

    # Ensure idempotency key is present
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")

    # TODO:
    # 1) Validate accounts via Account API
    # 2) Check status (ACTIVE), type (BASIC no overdraft)
    # 3) Enforce daily limit ₹2,00,000
    # 4) Create DEBIT + CREDIT entry
    # 5) Update amount in Account service (2 REST calls)
    # 6) Save idempotent response
    # 7) Fire async event → Notification service

    # Temporary mock response so API works
    return {
        "message": "transfer executed (stub)",
        "source_account_id": str(payload.source_account_id),
        "dest_account_id": str(payload.dest_account_id),
        "amount": payload.amount,
        "reference": payload.reference,
        "idempotency_key": idempotency_key,
    }
