# app/api/products.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import or_
from app import schemas, crud, models
from app.dependencies import get_db, get_current_admin

router = APIRouter(
    prefix="/products",
    tags=["products"]
)

@router.get("/search", response_model=List[schemas.ProductOut])
def search_products(
        category_id: Optional[int] = None,
        keyword: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        sort_by: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    query = db.query(models.Product)

    if category_id is not None:
        query = query.filter(models.Product.category_id == category_id)

    if keyword:
        query = query.filter(
            or_(
                models.Product.title.ilike(f"%{keyword}%"),
                models.Product.description.ilike(f"%{keyword}%")
            )
        )
    if min_price is not None:
        query = query.filter(models.Product.price >= min_price)
    if max_price is not None:
        query = query.filter(models.Product.price <= max_price)

    if sort_by:
        if sort_by == "price_asc":
            query = query.order_by(models.Product.price.asc())
        elif sort_by == "price_desc":
            query = query.order_by(models.Product.price.desc())
        elif sort_by == "name_asc":
            query = query.order_by(models.Product.title.asc())
        elif sort_by == "name_desc":
            query = query.order_by(models.Product.title.desc())

    return query.offset(skip).limit(limit).all()

@router.get("/", response_model=List[schemas.ProductOut])
def list_products(skip: int = 0, limit: int = 100, category_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Retrieve a list of products.
    Optionally filter by category using the 'category_id' query parameter.
    """
    if category_id:
        products = db.query(models.Product).filter(models.Product.category_id == category_id).offset(skip).limit(limit).all()
    else:
        products = crud.get_products(db, skip=skip, limit=limit)
    return products

@router.get("/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/", response_model=schemas.ProductOut, dependencies=[Depends(get_current_admin)])
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    return crud.create_product(db, product)

@router.put("/{product_id}", response_model=schemas.ProductOut, dependencies=[Depends(get_current_admin)])
def update_product(product_id: int, product: schemas.ProductCreate, db: Session = Depends(get_db)):
    updated_product = crud.update_product(db, product_id, product)
    if not updated_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return updated_product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
def delete_product(product_id: int, db: Session = Depends(get_db)):
    success = crud.delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return None
