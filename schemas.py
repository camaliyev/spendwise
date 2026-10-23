from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

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


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    category_id: int
    amount: Decimal
    description: str | None
    transaction_date: date

class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    kind: str

class CategoryCreate(BaseModel):
    user_id: int
    name: str
    kind: str