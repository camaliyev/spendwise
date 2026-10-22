from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Transaction
from schemas import TransactionCreate

app = FastAPI(title="SpendWise API")

@app.get("/")
def home():
    return {"message": "Welcome to the SpendWise API"}

@app.get("/transactions")
def list_transactions(db: Session = Depends(get_db)):
    transactions = db.scalars(select(Transaction)).all()
    return transactions

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
