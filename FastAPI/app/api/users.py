# app/api/users.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from app import schemas, crud, models
from app.dependencies import get_db, get_current_user, get_current_admin
from app.core.security import verify_password, create_access_token
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

@router.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if username already exists
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    # Check if email is already used
    db_email = crud.get_user_by_email(db, email=user.email)
    if db_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    # Create and return the new user
    created_user = crud.create_user(db, user)
    return created_user

@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Retrieve user by username
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Create JWT token for the user
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    """
    Retrieves details about the current authenticated user.
    """
    return current_user

@router.put("/me", response_model=schemas.UserOut)
def update_user_me(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the details of the currently authenticated user.
    Only the user themselves can update their data.
    """
    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/create-admin", response_model=schemas.UserOut, dependencies=[Depends(get_current_admin)])
def create_admin(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Create a new admin user.
    This endpoint can only be accessed by an already authenticated admin.
    """
    # Check if username already exists
    if crud.get_user_by_username(db, username=user.username):
        raise HTTPException(status_code=400, detail="Username already registered")

    # Check if email is already used
    if crud.get_user_by_email(db, email=user.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create the new admin user with the role "admin"
    new_admin = crud.create_user(db, user, role="admin")
    return new_admin


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
def delete_customer(user_id: int, db: Session = Depends(get_db)):
    """
    Delete a user (customer) along with all orders linked to that user.
    Only an admin can perform this action.
    For each order, the associated product inventory is restored.
    """
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete all orders linked to this user and restore product counts.
    # It's important to iterate over a copy of the orders list since the deletion
    # may modify the relationship.
    for order in list(user.orders):
        # Use the existing delete_order function to handle inventory restoration.
        success = crud.delete_order(db, order.id)
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to delete order with id {order.id}")

    # Now delete the user record.
    db.delete(user)
    db.commit()
    return None