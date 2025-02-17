# app/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import crud, models
from app.core.security import decode_access_token

# OAuth2 scheme for token extraction from the Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/token")

def get_db():
    """
    Dependency that provides a SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    """
    Dependency that retrieves the current user based on the JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    user = crud.get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception

    return user

def get_current_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    Dependency that ensures the current user has admin privileges.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions.")
    return current_user
