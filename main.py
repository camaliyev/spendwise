from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Transaction

app = FastAPI(title="SpendWise API")

@app.get("/")
def home():
    return {"message": "Welcome to the SpendWise API"}

@app.get("/transactions")
def list_transactions(db: Session = Depends(get_db)):
    transactions = db.scalars(select(Transaction)).all()
    return transactions