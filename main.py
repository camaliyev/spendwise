from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal
from sqlalchemy import func

from database import get_db
from models import Budget, Category, Transaction, User
from schemas import UserLogin, Token, UserCreate, UserRead, BudgetCreate, BudgetRead, BudgetSummary, BudgetUpdate, CategoryCreate, CategoryRead, CategoryUpdate, TransactionCreate, TransactionRead, TransactionUpdate
from sqlalchemy.exc import IntegrityError
from security import ALGORITHM, SECRET_KEY, hash_password, verify_password, create_access_token
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

app = FastAPI(title="SpendWise API")

@app.get("/")
def home():
    return {"message": "Welcome to the SpendWise API"}

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=401,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_error

    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp"]},
        )

        user_id = int(payload["sub"])
    except (InvalidTokenError, ValueError, TypeError):
        raise credentials_error

    user = db.get(User, user_id)

    if user is None:
        raise credentials_error

    return user

@app.get("/transactions", response_model=list[TransactionRead])
def list_transactions(
    category_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if start_date is not None and end_date is not None:
        if start_date > end_date:
            raise HTTPException(
                status_code=422,
                detail="Start date must not be after end date",
            )

    query = select(Transaction).where(
        Transaction.user_id == current_user.id
    )

    if category_id is not None:
        query = query.where(Transaction.category_id == category_id)

    if start_date is not None:
        query = query.where(Transaction.transaction_date >= start_date)

    if end_date is not None:
        query = query.where(Transaction.transaction_date <= end_date)

    query = query.order_by(Transaction.id).offset(offset).limit(limit)

    transactions = db.scalars(query).all()
    return transactions

@app.get("/transactions/{transaction_id}", response_model=TransactionRead)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = db.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id,
        )
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    return transaction

@app.delete("/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = db.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id,
        )
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    db.delete(transaction)
    db.commit()

    return {"message": "Transaction deleted successfully"}

@@app.patch("/transactions/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int,
    transaction_data: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = db.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id,
        )
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    update_data = transaction_data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=422,
            detail="No fields provided for update",
        )

    for field, value in update_data.items():
        if value is None and field != "description":
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null",
            )

    if "category_id" in update_data:
        category = db.scalar(
            select(Category).where(
                Category.id == update_data["category_id"],
                Category.user_id == current_user.id,
            )
        )

        if category is None:
            raise HTTPException(
                status_code=404,
                detail="Category not found",
            )

    for field, value in update_data.items():
        setattr(transaction, field, value)

    db.commit()
    db.refresh(transaction)
    return transaction

@app.post("/transactions", response_model=TransactionRead, status_code=201)
def create_transaction(
    transaction_data: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    category = db.scalar(
        select(Category).where(
            Category.id == transaction_data.category_id,
            Category.user_id == current_user.id,
        )
    )

    if category is None:
        raise HTTPException(
            status_code=404,
            detail="Category not found",
        )

    new_transaction = Transaction(
        user_id=current_user.id,
        **transaction_data.model_dump(),
    )

    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)
    return new_transaction


@app.get("/categories", response_model=list[CategoryRead])
def list_categories(db: Session = Depends(get_db)):
    categories = db.scalars(select(Category)).all()
    return categories

@app.post("/categories", response_model=CategoryRead, status_code=201)
def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
):
    new_category = Category(
        user_id=category_data.user_id,
        name=category_data.name,
        kind=category_data.kind,
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

@app.get("/categories/{category_id}", response_model=CategoryRead)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
):
    category = db.get(Category, category_id)

    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    return category

@app.patch("/categories/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
):
    category = db.get(Category, category_id)

    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    update_data = category_data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided")

    for field, value in update_data.items():
        if value is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null",
            )

    for field, value in update_data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return category

@app.delete("/categories/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
):
    category = db.get(Category, category_id)

    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    transaction_id =  db.scalar(
        select(Transaction.id)
        .where(Transaction.category_id == category_id)
        .limit(1)
    )

    budget_id = db.scalar(
        select(Budget.id)
        .where(Budget.category_id == category_id)
        .limit(1)
    )

    if transaction_id is not None or budget_id is not None:
        raise HTTPException(
            status_code=409,
            detail="Category is used by transactions or budgets",
        )

    db.delete(category)
    db.commit()

    return {"message": "Category deleted successfully"}


@app.get("/budgets", response_model=list[BudgetRead])
def list_budgets(db: Session = Depends(get_db)):
    budgets = db.scalars(select(Budget)).all()
    return budgets

@app.post("/budgets", response_model=BudgetRead, status_code=201)
def create_budget(
    budget_data: BudgetCreate,
    db: Session = Depends(get_db),
):
    category = db.get(Category, budget_data.category_id)

    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    if category.user_id != budget_data.user_id:
        raise HTTPException(
            status_code=422,
            detail="Category must belong to the budget's user",
        )

    if category.kind != "expense":
        raise HTTPException(
            status_code=422,
            detail="Budgets require an expense category",
        )

    new_budget = Budget(
        user_id=budget_data.user_id,
        category_id=budget_data.category_id,
        monthly_limit=budget_data.monthly_limit,
        month=budget_data.month,
    )

    db.add(new_budget)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Budget conflicts with existing database records",
        )

    db.refresh(new_budget)
    return new_budget

@app.get("/budgets/{budget_id}", response_model=BudgetRead)
def get_budget(
    budget_id: int,
    db: Session = Depends(get_db),
):
    budget = db.get(Budget, budget_id)

    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found")

    return budget

@app.patch("/budgets/{budget_id}", response_model=BudgetRead)
def update_budget(
    budget_id: int,
    budget_data: BudgetUpdate,
    db: Session = Depends(get_db),
):
    budget = db.get(Budget, budget_id)

    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found")

    budget.monthly_limit = budget_data.monthly_limit

    db.commit()
    db.refresh(budget)
    return budget

@app.delete("/budgets/{budget_id}")
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
):
    budget = db.get(Budget, budget_id)

    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found")

    db.delete(budget)
    db.commit()

    return {"message": "Budget deleted successfully"}


@app.get("/budgets/{budget_id}/summary", response_model=BudgetSummary)
def get_budget_summary(
    budget_id: int,
    db: Session = Depends(get_db),
):
    budget = db.get(Budget, budget_id)

    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found")

    start_date = budget.month

    if start_date.month == 12:
        end_date = date(start_date.year + 1, 1, 1)
    else:
        end_date = date(start_date.year, start_date.month + 1, 1)

    total_spent = db.scalar(
        select(func.sum(Transaction.amount)).where(
            Transaction.user_id == budget.user_id,
            Transaction.category_id == budget.category_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date < end_date,
        )
    )

    if total_spent is None:
        total_spent = Decimal("0.00")

    return {
        "budget_id": budget.id,
        "category_id": budget.category_id,
        "month": budget.month,
        "monthly_limit": budget.monthly_limit,
        "total_spent": total_spent,
        "remaining": budget.monthly_limit - total_spent,
    }

@app.post("/auth/register", response_model=UserRead, status_code=201)
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    existing_user = db.scalar(
        select(User).where(User.email == str(user_data.email))
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=409,
            detail="Email is already registered",
        )

    new_user = User(
        name=user_data.name,
        email=str(user_data.email),
        password_hash=hash_password(user_data.password),
    )

    db.add(new_user)

    try:
        db.commit()
    except IntegrityError:
        # Handle a duplicate registration that occurs after the initial check.
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Unable to register user with these details",
        )

    db.refresh(new_user)
    return new_user

@app.post("/auth/login", response_model=Token)
def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(User.email == str(user_data.email))
    )

    if user is None or not verify_password(
        user_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.id)

    return Token(access_token=access_token)

@app.get("/auth/me", response_model=UserRead)
def read_current_user(
    current_user: User = Depends(get_current_user)
):
    return current_user