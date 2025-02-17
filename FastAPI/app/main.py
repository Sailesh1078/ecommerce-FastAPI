# app/main.py

from fastapi import FastAPI
from app.database import engine, Base
from app.api import users, products, orders, categories

# Create all database tables (if they don't already exist)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FastAPI Ecommerce API",
    description="Ecommerce API using SQLite, with built-in Swagger and ReDoc documentation.",
    version="1.0.0"
)

app.include_router(users.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(categories.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI Ecommerce API"}
