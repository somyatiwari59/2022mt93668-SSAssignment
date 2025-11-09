# app/models/daily_ledger.py
from sqlalchemy import Column, Float, Date, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base

class DailyTransferLedger(Base):
    __tablename__ = "daily_transfer_ledger"

    account_id = Column(UUID(as_uuid=True), nullable=False)
    yyyymmdd  = Column(Date, nullable=False)
    debited   = Column(Float, default=0.0)

    __table_args__ = (
        PrimaryKeyConstraint("account_id", "yyyymmdd"),
    )
