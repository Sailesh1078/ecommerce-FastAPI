# routers/products.py
from typing import List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

router = APIRouter(
    prefix="/products",
    tags=["products"],
)

# --- Create Product (Admin Only) ---
@router.post("/", response_model=schemas.ProductSchema, status_code=201)
def create_product(
    product: schemas.ProductCreateSchema,
    db: Session = Depends(get_db),
    current_user: schemas.UserSchema = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.has_role("admin"))
):
    """
    Create a new product (admin only).
    """
    db_category = db.query(models.Category).filter(models.Category.id == product.category_id).first()
    if not db_category:
        raise HTTPException(status_code=400, detail="Invalid category_id")
    if product.price <= 0:
        raise HTTPException(status_code=400, detail="Price must be a positive value")
    if product.quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be negative")

    db_product = models.Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

# --- List Products (Public - with search, filter, pagination) ---
@router.get("/", response_model=schemas.ProductListResponse)
def read_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    category_id: Optional[int] = Query(default=None),
    search: Optional[str] = Query(default=None),
    min_price: Optional[float] = Query(default=None, ge=0), # Price range filter
    max_price: Optional[float] = Query(default=None, ge=0), # Price range filter
    db: Session = Depends(get_db)
):
    """
    List products with search, category filter, and pagination (public access).
    """
    query = db.query(models.Product)

    if category_id:
        db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
        if not db_category:
            raise HTTPException(status_code=400, detail="Invalid category_id")
        query = query.filter(models.Product.category_id == category_id)
    if search:
        query = query.filter(models.Product.name.contains(search))
    if min_price is not None:
        query = query.filter(models.Product.price >= min_price)
    if max_price is not None:
        query = query.filter(models.Product.price <= max_price)

    total_products = query.count()
    products = query.offset(skip).limit(limit).all()

    product_schemas = []
    for prod in products:
        category_schema = schemas.CategorySchema.from_orm(prod.category) # Eagerly load category
        product_schema = schemas.ProductSchema.from_orm(prod)
        product_schema.category = category_schema
        product_schemas.append(product_schema)


    return schemas.ProductListResponse(
        items=product_schemas,
        total=total_products,
        skip=skip,
        limit=limit,
        category_id_filter=category_id, # Include filter info in response
        search_query=search # Include search query info in response
    )

# --- Get Product by ID (Public) ---
@router.get("/{product_id}", response_model=schemas.ProductSchema)
def read_product(product_id: int, db: Session = Depends(get_db)):
    """
    Get a product by its ID (public access).
    """
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    category_schema = schemas.CategorySchema.from_orm(db_product.category) # Eagerly load category
    product_schema = schemas.ProductSchema.from_orm(db_product)
    product_schema.category = category_schema
    return product_schema

# --- Update Product (Admin Only) ---
@router.put("/{product_id}", response_model=schemas.ProductSchema)
def update_product(
    product_id: int,
    product_update: schemas.ProductUpdateSchema,
    db: Session = Depends(get_db),
    current_user: schemas.UserSchema = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.has_role("admin"))
):
    """
    Update a product (admin only).
    """
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if product_update.category_id:
        db_category = db.query(models.Category).filter(models.Category.id == product_update.category_id).first()
        if not db_category:
            raise HTTPException(status_code=400, detail="Invalid category_id")
    if product_update.price is not None and product_update.price <= 0:
        raise HTTPException(status_code=400, detail="Price must be a positive value")
    if product_update.quantity is not None and product_update.quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be negative")


    for field, value in product_update.dict(exclude_unset=True).items():
        setattr(db_product, field, value)
    db.commit()
    db.refresh(db_product)
    category_schema = schemas.CategorySchema.from_orm(db_product.category) # Eagerly load category
    product_schema = schemas.ProductSchema.from_orm(db_product)
    product_schema.category = category_schema
    return product_schema

# --- Delete Product (Admin Only) ---
@router.delete("/{product_id}", status_code=200)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.UserSchema = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.has_role("admin"))
):
    """
    Delete a product (admin only).
    """
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(db_product)
    db.commit()
    return {"message": "Product deleted successfully"}

# --- Update Product Quantity (Admin Only) ---
@router.put("/{product_id}/quantity", response_model=schemas.ProductSchema)
def update_product_quantity(
    product_id: int,
    quantity_update: Dict = Body(...), # Expecting JSON body with {"quantity": integer}
    db: Session = Depends(get_db),
    current_user: schemas.UserSchema = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.has_role("admin"))
):
    """
    Update the quantity of a product (admin only).
    """
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    new_quantity = quantity_update.get("quantity")
    if new_quantity is None or not isinstance(new_quantity, int) or new_quantity < 0:
        raise HTTPException(status_code=400, detail="Invalid quantity value. Must be a non-negative integer.")

    db_product.quantity = new_quantity
    db.commit()
    db.refresh(db_product)
    category_schema = schemas.CategorySchema.from_orm(db_product.category) # Eagerly load category
    product_schema = schemas.ProductSchema.from_orm(db_product)
    product_schema.category = category_schema
    return db_product