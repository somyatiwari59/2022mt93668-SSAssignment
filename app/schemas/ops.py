import uuid
from typing import Optional
from pydantic import BaseModel, Field

class MoneyIn(BaseModel):
    account_id: uuid.UUID
    amount: float = Field(gt=0)
    reference: Optional[str] = None
    counterparty: Optional[str] = None
