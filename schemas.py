from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


# Users and authentication


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=15, max_length=128)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Name cannot be blank")

        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    created_at: datetime


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


# Transactions


class TransactionCreate(BaseModel):
    category_id: int
    amount: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=2,
    )
    description: str | None = Field(default=None, max_length=255)
    transaction_date: date


class TransactionUpdate(BaseModel):
    amount: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2,
    )
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=255)
    transaction_date: date | None = None


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    category_id: int
    amount: Decimal
    description: str | None
    transaction_date: date


# Categories


class CategoryCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=50)
    kind: Literal["income", "expense"]


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )
    kind: Literal["income", "expense"] | None = None


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    kind: Literal["income", "expense"]


# Budgets


class BudgetCreate(BaseModel):
    category_id: int
    monthly_limit: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=2,
    )
    month: date

    @field_validator("month")
    @classmethod
    def validate_month(cls, value: date) -> date:
        if value.day != 1:
            raise ValueError("Month must be the first day of the month")

        return value


class BudgetUpdate(BaseModel):
    monthly_limit: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=2,
    )


class BudgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    category_id: int
    monthly_limit: Decimal
    month: date


class BudgetSummary(BaseModel):
    budget_id: int
    category_id: int
    month: date
    monthly_limit: Decimal
    total_spent: Decimal
    remaining: Decimal