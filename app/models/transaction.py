# app/models/transaction.py
from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.db.session import Base

class Transaction(Base):
    __tablename__ = "transactions"

    txn_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), nullable=False)
    amount = Column(Float, nullable=False)
    txn_type = Column(String, nullable=False)
    counterparty = Column(String, nullable=True)
    reference = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
