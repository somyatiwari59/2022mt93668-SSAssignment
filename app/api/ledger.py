# app/api/ledger.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Literal, Optional
import datetime as dt
import uuid
from zoneinfo import ZoneInfo
from sqlalchemy import asc, desc, func, case
from app.models.transaction import Transaction
from app.db.session import SessionLocal
from app.models.daily_ledger import DailyTransferLedger

router = APIRouter(tags=["ledger"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _to_date(s: Optional[str]) -> dt.date:
    if not s:
        return dt.date.today()
    try:
        return dt.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, detail="Invalid date format. Use YYYY-MM-DD.")

@router.get("/accounts/{account_id}/daily-ledger")
def get_daily_ledger(
    account_id: uuid.UUID,
    date: Optional[str] = Query(None, description="YYYY-MM-DD; defaults to today"),
    limit: float = Query(200000.0, gt=0, description="Daily debit limit to compute remaining"),
    db: Session = Depends(get_db),
):
    d = _to_date(date)
    rec = db.get(DailyTransferLedger, {"account_id": account_id, "yyyymmdd": d})
    used = float(rec.debited) if rec else 0.0
    remaining = limit - used
    if remaining < 0:
        remaining = 0.0
    return {
        "account_id": str(account_id),
        "date": d.isoformat(),
        "used_today": used,
        "limit": limit,
        "remaining": remaining,
        "has_row": rec is not None
    }

@router.get("/accounts/{account_id}/daily-ledger/history")
def get_daily_ledger_history(
    account_id: uuid.UUID,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Last N days of debited totals (including today)."""
    today = dt.date.today()
    start = today - dt.timedelta(days=days - 1)
    rows = (
        db.query(DailyTransferLedger)
          .filter(
              DailyTransferLedger.account_id == account_id,
              DailyTransferLedger.yyyymmdd >= start,
              DailyTransferLedger.yyyymmdd <= today,
          )
          .order_by(DailyTransferLedger.yyyymmdd.asc())
          .all()
    )
    # build a dense series (0 for missing days)
    by_day = {r.yyyymmdd: float(r.debited) for r in rows}
    series = []
    for i in range(days):
        d = start + dt.timedelta(days=i)
        series.append({"date": d.isoformat(), "debited": by_day.get(d, 0.0)})
    return {"account_id": str(account_id), "days": days, "series": series}


def _day_window_utc(day: dt.date, tz_name: str = "Asia/Kolkata"):
    """Return (start_utc, end_utc) for the given local day in tz."""
    tz = ZoneInfo(tz_name)
    start_local = dt.datetime.combine(day, dt.time.min).replace(tzinfo=tz)
    end_local = start_local + dt.timedelta(days=1)
    return start_local.astimezone(dt.timezone.utc), end_local.astimezone(dt.timezone.utc)

@router.get("/accounts/{account_id}/daily-ledger/transactions")
def get_daily_ledger_with_transactions(
    account_id: uuid.UUID,
    date: Optional[str] = Query(None, description="YYYY-MM-DD; defaults to today"),
    tz: str = Query("Asia/Kolkata", description="IANA TZ for day window"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    order: Literal["asc", "desc"] = Query("desc"),
    db: Session = Depends(get_db),
):
    """
    Returns daily totals (debited, credited, net) + list of that day's transactions.
    Uses timezone-aware day window; defaults to Asia/Kolkata.
    """
    d = _to_date(date)
    start_utc, end_utc = _day_window_utc(d, tz)

    base = (
        db.query(Transaction)
          .filter(
              Transaction.account_id == account_id,
              Transaction.created_at >= start_utc,
              Transaction.created_at < end_utc,
          )
    )

    # totals (no pagination)
    debit_sum, credit_sum, total_count = (
        db.query(
            func.coalesce(
                func.sum(case((Transaction.txn_type == "DEBIT", Transaction.amount), else_=0.0)),
                0.0,
            ),
            func.coalesce(
                func.sum(case((Transaction.txn_type == "CREDIT", Transaction.amount), else_=0.0)),
                0.0,
            ),
            func.count(),
        )
        .filter(
            Transaction.account_id == account_id,
            Transaction.created_at >= start_utc,
            Transaction.created_at < end_utc,
        )
        .one()
    )

    # page of items
    ordering = Transaction.created_at.asc() if order == "asc" else Transaction.created_at.desc()
    items = (
        base.order_by(ordering)
            .limit(limit)
            .offset(offset)
            .all()
    )

    return {
        "account_id": str(account_id),
        "date": d.isoformat(),
        "timezone": tz,
        "totals": {
            "debited": float(debit_sum),
            "credited": float(credit_sum),
            "net": float(credit_sum - debit_sum),
            "count": int(total_count),
        },
        "pagination": {
            "limit": limit,
            "offset": offset,
            "returned": len(items),
        },
        "transactions": [
            {
                "txn_id": str(t.txn_id),
                "type": t.txn_type,
                "amount": float(t.amount),
                "counterparty": t.counterparty,
                "reference": t.reference,
                "created_at": t.created_at.isoformat(),
            }
            for t in items
        ],
    }