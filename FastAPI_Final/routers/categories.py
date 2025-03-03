# routers/categories.py
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

router = APIRouter(
    prefix="/categories",
    tags=["categories"],
)

# --- Create Category (Admin Only) ---
@router.post("/", response_model=schemas.CategorySchema, status_code=201)
def create_category(
    category: schemas.CategoryCreateSchema,
    db: Session = Depends(get_db),
    current_user: schemas.UserSchema = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.has_role("admin"))
):
    """
    Create a new category (admin only).
    """
    db_category = db.query(models.Category).filter(models.Category.name == category.name).first()
    if db_category:
        raise HTTPException(status_code=409, detail="Category name already exists")
    db_category = models.Category(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

# --- List Categories (Public - with pagination) ---
@router.get("/", response_model=schemas.CategoryListResponse)
def read_categories(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List categories with pagination (public access).
    """
    categories = db.query(models.Category).offset(skip).limit(limit).all()
    total_categories = db.query(models.Category).count()
    category_schemas = []
    for cat in categories:
        product_count = db.query(models.Product).filter(models.Product.category_id == cat.id).count()
        category_schema = schemas.CategorySchema.from_orm(cat)
        category_schema.product_count = product_count # Add product_count
        category_schemas.append(category_schema)

    return schemas.CategoryListResponse(
        items=category_schemas,
        total=total_categories,
        skip=skip,
        limit=limit
    )

# --- Get Category by ID (Public) ---
@router.get("/{category_id}", response_model=schemas.CategorySchema)
def read_category(category_id: int, db: Session = Depends(get_db)):
    """
    Get a category by its ID (public access).
    """
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    product_count = db.query(models.Product).filter(models.Product.category_id == db_category.id).count()
    category_schema = schemas.CategorySchema.from_orm(db_category)
    category_schema.product_count = product_count # Add product_count
    return category_schema

# --- Update Category (Admin Only) ---
@router.put("/{category_id}", response_model=schemas.CategorySchema)
def update_category(
    category_id: int,
    category_update: schemas.CategoryUpdateSchema,
    db: Session = Depends(get_db),
    current_user: schemas.UserSchema = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.has_role("admin"))
):
    """
    Update a category (admin only).
    """
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if category_update.name: # Check if name is being updated and if new name already exists
        existing_category_name = db.query(models.Category).filter(models.Category.name == category_update.name).first()
        if existing_category_name and existing_category_name.id != category_id:
            raise HTTPException(status_code=409, detail="Category name already exists")

    for field, value in category_update.dict(exclude_unset=True).items():
        setattr(db_category, field, value)
    db.commit()
    db.refresh(db_category)
    product_count = db.query(models.Product).filter(models.Product.category_id == db_category.id).count()
    category_schema = schemas.CategorySchema.from_orm(db_category)
    category_schema.product_count = product_count # Add product_count
    return category_schema

# --- Delete Category (Admin Only) ---
@router.delete("/{category_id}", status_code=200)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.UserSchema = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.has_role("admin"))
):
    """
    Delete a category (admin only).
    """
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    product_count = db.query(models.Product).filter(models.Product.category_id == category_id).count()
    if product_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete category with associated products. Please reassign or delete products first."
        )

    db.delete(db_category)
    db.commit()
    return {"message": "Category deleted successfully"}