# app/crud.py

from sqlalchemy.orm import Session
from typing import List, Optional
from app import models, schemas
from app.core.security import get_password_hash  # Assuming this is already implemented

# ---------------------------
# User CRUD Operations
# ---------------------------
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate, role: str = "customer") -> models.User:
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# ---------------------------
# Product CRUD Operations
# ---------------------------
def get_product(db: Session, product_id: int) -> Optional[models.Product]:
    return db.query(models.Product).filter(models.Product.id == product_id).first()

def get_products(db: Session, skip: int = 0, limit: int = 100) -> List[models.Product]:
    return db.query(models.Product).offset(skip).limit(limit).all()

def create_product(db: Session, product: schemas.ProductCreate) -> models.Product:
    # Check if a product with the same title and category exists
    existing_product = db.query(models.Product).filter(
        models.Product.title == product.title,
        models.Product.category_id == product.category_id
    ).first()
    if existing_product:
        # If it exists, increment the count
        increment = product.count if product.count is not None else 1
        existing_product.count += increment
        db.commit()
        db.refresh(existing_product)
        return existing_product
    else:
        db_product = models.Product(**product.dict())
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product

def update_product(db: Session, product_id: int, product: schemas.ProductCreate) -> Optional[models.Product]:
    db_product = get_product(db, product_id)
    if db_product:
        for key, value in product.dict().items():
            setattr(db_product, key, value)
        db.commit()
        db.refresh(db_product)
    return db_product

def delete_product(db: Session, product_id: int) -> bool:
    db_product = get_product(db, product_id)
    if db_product:
        db.delete(db_product)
        db.commit()
        return True
    return False

# ---------------------------
# Order CRUD Operations
# ---------------------------
def get_order(db: Session, order_id: int) -> Optional[models.Order]:
    return db.query(models.Order).filter(models.Order.id == order_id).first()

def get_orders_by_user(db: Session, user_id: int) -> List[models.Order]:
    return db.query(models.Order).filter(models.Order.user_id == user_id).all()

def create_order(db: Session, user_id: int, order: schemas.OrderCreate) -> models.Order:
    db_order = models.Order(user_id=user_id)
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    for item in order.order_items:
        db_item = models.OrderItem(
            order_id=db_order.id,
            product_id=item.product_id,
            quantity=item.quantity
        )
        db.add(db_item)
    db.commit()
    db.refresh(db_order)
    return db_order
def update_order(db: Session, order_id: int, new_order: schemas.OrderCreate) -> Optional[models.Order]:
    """
    Update an order by:
      1. Restoring the product count for all items in the existing order.
      2. Removing the old order items.
      3. Adding new order items and deducting product count accordingly.
    """
    existing_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not existing_order:
        return None

    # Restore inventory for all existing order items
    for item in existing_order.order_items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if product:
            product.count += item.quantity  # restore count
        db.delete(item)  # remove the existing order item
    db.commit()

    # Process new order items
    for new_item in new_order.order_items:
        product = db.query(models.Product).filter(models.Product.id == new_item.product_id).first()
        if not product or product.count < new_item.quantity:
            db.rollback()
            raise HTTPException(status_code=400, detail="Insufficient inventory for product ID {}".format(new_item.product_id))
        product.count -= new_item.quantity
        db_order_item = models.OrderItem(
            order_id=order_id,
            product_id=new_item.product_id,
            quantity=new_item.quantity
        )
        db.add(db_order_item)
    db.commit()
    db.refresh(existing_order)
    return existing_order
def delete_order(db: Session, order_id: int) -> bool:
    """
    Delete an order and restore the product inventory based on the order items.
    """
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        return False

    # Restore inventory for each order item
    for item in order.order_items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if product:
            product.count += item.quantity
        db.delete(item)
    db.delete(order)
    db.commit()
    return True

# ---------------------------
# Category CRUD Operations
# ---------------------------
def get_categories(db: Session) -> List[models.Category]:
    return db.query(models.Category).all()

def get_category(db: Session, category_id: int) -> Optional[models.Category]:
    return db.query(models.Category).filter(models.Category.id == category_id).first()

def get_category_by_name(db: Session, name: str) -> Optional[models.Category]:
    return db.query(models.Category).filter(models.Category.name == name).first()

def create_category(db: Session, category: schemas.CategoryCreate) -> models.Category:
    db_category = models.Category(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category
