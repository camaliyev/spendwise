from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Transaction
from schemas import TransactionCreate, TransactionUpdate

app = FastAPI(title="SpendWise API")

@app.get("/")
def home():
    return {"message": "Welcome to the SpendWise API"}

@app.get("/transactions")
def list_transactions(db: Session = Depends(get_db)):
    transactions = db.scalars(select(Transaction)).all()
    return transactions

@app.get("/transactions/{transaction_id}")
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    transaction = db.get(Transaction, transaction_id)

    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return transaction

@app.delete("/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    transaction = db.get(Transaction, transaction_id)

    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(transaction)
    db.commit()

    return {"message": "Transaction deleted successfully"}

@app.patch("/transactions/{transaction_id}")
def update_transaction(
    transaction_id: int,
    transaction_data: TransactionUpdate,
    db: Session = Depends(get_db),
):
    transaction = db.get(Transaction, transaction_id)

    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    update_data = transaction_data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided")

    for field, value in update_data.items():
        if value is None and field != "description":
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null",
            )
        setattr(transaction, field, value)

    db.commit()
    db.refresh(transaction)
    return transaction


@app.post("/transactions")
def create_transaction(
    transaction_data: TransactionCreate,
    db: Session = Depends(get_db)
):
     new_transaction = Transaction(**transaction_data.model_dump())
     db.add(new_transaction)
     db.commit()
     db.refresh(new_transaction)
     return new_transaction
