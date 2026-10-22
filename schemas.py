from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field

class TransactionCreate(BaseModel):
    user_id: int
    category_id: int
    amount: Decimal = Field(gt=0)
    description: str | None = None
    transaction_date: date


class TransactionUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    category_id: int | None = None
    description: str | None = None
    transaction_date: date | None = None

