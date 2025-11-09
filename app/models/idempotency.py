from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from app.db.session import Base

class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    key = Column(String, primary_key=True)    # Idempotency-Key
    response = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
