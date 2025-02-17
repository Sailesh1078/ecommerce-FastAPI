# app/api/orders.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import schemas, crud, models
from app.dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/orders",
    tags=["orders"]
)

@router.post("/", response_model=schemas.OrderOut)
def create_order(
    order: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a new order for the authenticated user.
    Deduct product inventory based on the order items.
    """
    # Deduct product counts
    for item in order.order_items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product or product.count < item.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient inventory for product ID {item.product_id}")
        product.count -= item.quantity
    db.commit()
    # Create the order record
    return crud.create_order(db, user_id=current_user.id, order=order)

@router.get("/", response_model=List[schemas.OrderOut])
def list_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieve all orders for the authenticated user.
    """
    orders = crud.get_orders_by_user(db, user_id=current_user.id)
    return orders

@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieve a specific order by its ID, only if it belongs to the current user.
    """
    order = crud.get_order(db, order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.put("/{order_id}", response_model=schemas.OrderOut)
def update_order_endpoint(
    order_id: int,
    order: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Update an existing order.
    Only the owner of the order can update it.
    The update restores previous product counts and applies new ones.
    """
    existing_order = crud.get_order(db, order_id)
    if not existing_order or existing_order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found or unauthorized")
    updated_order = crud.update_order(db, order_id, order)
    return updated_order

@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order_endpoint(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Delete an order. Only the owner of the order can delete it.
    Restores the product counts based on the order items.
    """
    existing_order = crud.get_order(db, order_id)
    if not existing_order or existing_order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found or unauthorized")
    success = crud.delete_order(db, order_id)
    if not success:
        raise HTTPException(status_code=400, detail="Unable to delete order")
    return None