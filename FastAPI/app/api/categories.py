# app/api/categories.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import schemas, crud, models
from app.dependencies import get_db, get_current_admin

router = APIRouter(
    prefix="/categories",
    tags=["categories"]
)

@router.get("/", response_model=List[schemas.CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    categories = crud.get_categories(db)
    return categories

@router.get("/{category_id}", response_model=schemas.CategoryOut)
def get_category(category_id: int, db: Session = Depends(get_db)):
    category = crud.get_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@router.post("/", response_model=schemas.CategoryOut, dependencies=[Depends(get_current_admin)])
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    # Check if the category already exists
    if crud.get_category_by_name(db, name=category.name):
        raise HTTPException(status_code=400, detail="Category already exists")
    new_category = crud.create_category(db, category)
    return new_category

@router.put("/{category_id}", response_model=schemas.CategoryOut, dependencies=[Depends(get_current_admin)])
def update_category(category_id: int, category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    db_category = crud.get_category(db, category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    # Update the category fields
    db_category.name = category.name
    db_category.description = category.description
    db.commit()
    db.refresh(db_category)
    return db_category

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
def delete_category(category_id: int, db: Session = Depends(get_db)):
    db_category = crud.get_category(db, category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    # Optionally, prevent deletion if products exist in the category
    if db_category.products:
        raise HTTPException(status_code=400, detail="Category cannot be deleted because it has associated products")
    db.delete(db_category)
    db.commit()
    return None
