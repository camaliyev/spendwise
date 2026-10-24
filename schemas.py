from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    user_id: int
    category_id: int
    amount: Decimal = Field(gt=0)
    description: str | None = None
    transaction_date: date


class TransactionUpdate(BaseModel):
    # Use exclude_unset=True in the route to preserve omitted fields.
    # Explicit null is allowed only for description; the route enforces this.
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
    # Strip whitespace before length validation to reject blank names.
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: int
    name: str = Field(min_length=1, max_length=50)
    kind: Literal["income", "expense"]

class CategoryUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=50)
    kind: Literal["income", "expense"] | None = None