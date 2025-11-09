from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.schemas.ops import MoneyIn
from app.models.transaction import Transaction
from app.models.daily_ledger import DailyTransferLedger
from app.services import account_client as acct
from typing import Optional
import datetime as dt

router = APIRouter(prefix="", tags=["money"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def _today() -> dt.date: return dt.date.today()

def _check_daily_limit(db: Session, account_id, add_amount: float, limit: float = 200000):
    rec = db.get(DailyTransferLedger, {"account_id": account_id, "yyyymmdd": _today()})
    deb = float(rec.debited) if rec else 0.0
    if deb + add_amount > limit:
        raise HTTPException(422, detail=f"Daily limit exceeded (₹{limit:,.0f})")

def _bump_ledger(db: Session, account_id, amount: float):
    d = _today()
    rec = db.get(DailyTransferLedger, {"account_id": account_id, "yyyymmdd": d})
    if rec:
        rec.debited = rec.debited + amount
    else:
        db.add(DailyTransferLedger(account_id=account_id, yyyymmdd=d, debited=amount))

@router.post("/deposit", status_code=201)
def deposit(inb: MoneyIn, db: Session = Depends(get_db), idempotency_key: Optional[str] = Header(None)):
    acc = acct.get_account(inb.account_id)
    if acc["status"] != "ACTIVE":
        raise HTTPException(409, detail=f"Account not ACTIVE (status={acc['status']})")

    # 1) Record CREDIT transaction
    with db.begin():
        tx = Transaction(
            account_id=inb.account_id, amount=inb.amount, txn_type="CREDIT",
            counterparty=inb.counterparty, reference=inb.reference
        )
        db.add(tx)

    # 2) Update Account balance (+amount)
    try:
        acct.update_amount(inb.account_id, +inb.amount, idempotency_key)
    except acct.AccountConflict as e:
        raise HTTPException(409, detail=str(e))
    except Exception as e:
        raise HTTPException(502, detail=f"Account update failed: {e}")

    return {"txn_id": str(tx.txn_id), "type": "CREDIT", "amount": inb.amount}

@router.post("/withdraw", status_code=201)
def withdraw(inb: MoneyIn, db: Session = Depends(get_db), idempotency_key: Optional[str] = Header(None)):
    acc = acct.get_account(inb.account_id)
    if acc["status"] != "ACTIVE":
        raise HTTPException(409, detail=f"Account not ACTIVE (status={acc['status']})")

    # Business rules
    if acc["type"] == "BASIC" and inb.amount > acc["balance"]:
        raise HTTPException(409, detail="Insufficient funds for BASIC (no overdraft)")
    _check_daily_limit(db, inb.account_id, inb.amount)

    # 1) Record DEBIT transaction & bump daily ledger
    with db.begin():
        tx = Transaction(
            account_id=inb.account_id, amount=inb.amount, txn_type="DEBIT",
            counterparty=inb.counterparty, reference=inb.reference
        )
        db.add(tx)
        _bump_ledger(db, inb.account_id, inb.amount)

    # 2) Update Account balance (-amount)
    try:
        acct.update_amount(inb.account_id, -inb.amount, idempotency_key)
    except acct.AccountConflict as e:
        raise HTTPException(409, detail=str(e))
    except Exception as e:
        raise HTTPException(502, detail=f"Account update failed: {e}")

    return {"txn_id": str(tx.txn_id), "type": "DEBIT", "amount": inb.amount}
