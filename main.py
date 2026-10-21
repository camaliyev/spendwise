from fastapi import FastAPI

app = FastAPI(title="SpendWise API")

@app.get("/")
def home():
    return {"message": "Welcome to the SpendWise API"}