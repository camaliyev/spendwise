from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field

class TransactionCreate(BaseModel):
    user_id: int
    category_id: int
    amount: Decimal = Field(gt=0)
    description: str | None = None
    transaction_date: date

    