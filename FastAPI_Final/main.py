# main.py
from typing import List
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db, engine, SessionLocal
import models
import schemas
import auth
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
from routers import categories, products, users, orders # Import routers
from auth import router as auth_router # Import auth router

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# --- Include Routers ---
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(users.router)
app.include_router(orders.router)
app.include_router(auth_router)


# --- Initialize Roles ---
def initialize_roles(db: Session):
    roles = ["admin", "customer"]
    for role_name in roles:
        db_role = db.query(models.Role).filter(models.Role.name == role_name).first()
        if not db_role:
            db_role = models.Role(name=role_name)
            db.add(db_role)
    db.commit()

@app.on_event("startup")
async def startup_event():
    db = SessionLocal() # Use SessionLocal directly here
    initialize_roles(db)
    db.close()


# --- Error Handling ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(f"RequestValidationError: {exc}") # Log details for debugging
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )


@app.get("/protected")
async def protected_endpoint(current_user: auth.TokenData = Depends(auth.get_current_user)):
    return {
        "message": f"Hello {current_user.username}, you are authenticated!",
        "roles": current_user.roles,
    }


@app.get("/public")
async def public_endpoint():
    return {"message": "This is a public endpoint accessible to everyone."}