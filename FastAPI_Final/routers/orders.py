# routers/orders.py
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session, joinedload
from typing import List
from database import get_db
import models, schemas, auth
from datetime import datetime
from pydantic import BaseModel

router = APIRouter(
    prefix="/orders",
    tags=["Orders"]
)

# --- Cart Item Endpoints (OrderItem - for shopping cart) ---
@router.post("/items/", response_model=schemas.OrderItemSchema, status_code=status.HTTP_201_CREATED) # POST /orders/items/ to add item to cart
def create_cart_item(order_item: schemas.OrderItemCreate, db: Session = Depends(get_db), current_user: auth.TokenData = Depends(auth.get_current_user)):
    """
    Add a product to the user's shopping cart (customer or admin).
    If the item is already in the cart, it increases the quantity. Otherwise, it adds a new item.
    """
    user_id = auth.get_current_user_local_db(current_user, db).id
    db_product = db.query(models.Product).filter(models.Product.id == order_item.product_id).first()
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if db_product.quantity < order_item.quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficient stock for '{db_product.name}'. Only {db_product.quantity} available.")

    # Check if item already in cart
    db_cart_item = db.query(models.OrderItem).filter(
        models.OrderItem.user_id == user_id,
        models.OrderItem.product_id == order_item.product_id
    ).first()

    if db_cart_item: # If item exists, update quantity
        db_cart_item.quantity += order_item.quantity
    else: # If item not in cart, create new cart item
        db_cart_item = models.OrderItem(
            user_id=user_id,
            product_id=order_item.product_id,
            quantity=order_item.quantity,
            price=db_product.price # Store current price in cart item
        )
        db.add(db_cart_item)

    db.commit()
    db.refresh(db_cart_item)
    return db_cart_item


@router.get("/items/", response_model=List[schemas.OrderItemSchema]) # GET /orders/items/ to view cart items
def read_cart_items_for_current_user(db: Session = Depends(get_db), current_user: auth.TokenData = Depends(auth.get_current_user)):
    """
    Get all items in the current user's shopping cart (customer or admin).
    Returns a list of OrderItem objects that have order_id = NULL (cart items).
    """
    user_id = auth.get_current_user_local_db(current_user, db).id
    cart_items = db.query(models.OrderItem).filter(models.OrderItem.user_id == user_id).all() # Corrected to use .is_(None)
    return cart_items

@router.delete("/items/{order_item_id}", response_model=schemas.OrderItemSchema) # DELETE /orders/items/{order_item_id} to delete cart item
def delete_cart_item(order_item_id: int, db: Session = Depends(get_db), current_user: auth.TokenData = Depends(auth.get_current_user)):
    """
    Delete a specific item from the user's shopping cart (customer or admin).
    """
    user_id = auth.get_current_user_local_db(current_user, db).id
    db_cart_item = db.query(models.OrderItem).options(joinedload(models.OrderItem.product)).filter( # <--- Eager load product relationship
        models.OrderItem.id == order_item_id,
        models.OrderItem.user_id == user_id
    ).first()
    if not db_cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    db.delete(db_cart_item)
    db.commit()
    return db_cart_item

@router.put("/items/{order_item_id}", response_model=schemas.OrderItemSchema) # PUT /orders/items/{order_item_id} to update cart item quantity
def update_cart_item_quantity(order_item_id: int, order_item_update: schemas.OrderItemCreate, db: Session = Depends(get_db), current_user: auth.TokenData = Depends(auth.get_current_user)):
    """
    Update the quantity of a specific item in the user's shopping cart (customer or admin).
    """
    user_id = auth.get_current_user_local_db(current_user, db).id
    db_cart_item = db.query(models.OrderItem).filter(models.OrderItem.id == order_item_id, models.OrderItem.user_id == user_id).first() # Corrected to use .is_(None)
    if not db_cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    db_product = db.query(models.Product).filter(models.Product.id == order_item_update.product_id).first()
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if db_product.quantity < order_item_update.quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficient stock for '{db_product.name}'. Only {db_product.quantity} available.")

    db_cart_item.quantity = order_item_update.quantity
    db.commit()
    db.refresh(db_cart_item)
    return db_cart_item


# --- Order Endpoints (Order and OrderLineItem - for placed orders) ---
@router.post("/", response_model=schemas.OrderSchema, status_code=status.HTTP_201_CREATED) # POST /orders/ to place order from cart
def create_order_from_cart(order_create: schemas.OrderCreate, db: Session = Depends(get_db), current_user: auth.TokenData = Depends(auth.get_current_user)):
    """
    Create a new order by converting items from the user's shopping cart (customer or admin).
    Takes items from the current user's cart (OrderItem table where order_id is NULL),
    creates a new Order and OrderLineItems, and empties the cart (deletes cart items).
    """
    user_id = auth.get_current_user_local_db(current_user, db).id
    cart_items = db.query(models.OrderItem).filter(models.OrderItem.user_id == user_id, models.OrderItem.order_id.is_(None)).all() # Corrected to use .is_(None)
    if not cart_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot create order with an empty cart.")

    db_order_line_items_for_order = [] # To hold OrderLineItems to be created
    total_quantity = 0
    total_amount = 0

    for cart_item in cart_items:
        db_product = db.query(models.Product).filter(models.Product.id == cart_item.product_id).first()
        if db_product.quantity < cart_item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for '{db_product.name}'. Only {db_product.quantity} available."
            )

        # Create OrderLineItem from cart item
        db_order_line_item = models.OrderLineItem(
            order_id=None, # Order ID will be set after Order is created
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            price=cart_item.price # Use price from cart item (price at time of cart addition)
        )
        db_order_line_items_for_order.append(db_order_line_item) # Add to list for association with Order
        total_quantity += cart_item.quantity
        total_amount += cart_item.price * cart_item.quantity
        db_product.quantity -= cart_item.quantity # Reduce product quantity


    db_order = models.Order(
        user_id=user_id,
        order_date=datetime.utcnow(),
        status="pending",
        order_line_items=db_order_line_items_for_order # Associate OrderLineItems with Order
    )

    try:
        db.add(db_order)
        db.commit()
        db.refresh(db_order)

        # Now that order is created and has an ID, set order_id for order_line_items
        for db_order_line_item in db_order_line_items_for_order:
            db_order_line_item.order_id = db_order.id

        db.commit() # Commit again to update order_line_items with order_id

        # --- DELETE CART ITEMS AFTER ORDER CREATION (Empty the cart) ---
        for cart_item in cart_items:
            db.delete(cart_item) # Delete each cart item from the database
        db.commit() # Commit the deletion of cart items


        return read_order(order_id=db_order.id, db=db, current_user=current_user) # Return full order details using read_order function
    except Exception as e:
        db.rollback() # Rollback product quantity changes if order fails
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not create order. Database error: {e}")

@router.get("/{order_id}", response_model=schemas.OrderSchema) # GET /orders/{order_id} to view order details
def read_order(order_id: int, db: Session = Depends(get_db), current_user: auth.TokenData = Depends(auth.get_current_user)):
    """
    Get details of a specific order by order ID.
    Admins can view any order, customers can only view their own orders.
    Includes associated order line items and user details.
    """
    user_id = auth.get_current_user_local_db(current_user, db).id
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if not auth.is_admin(current_user.roles) and db_order.user_id != user_id: # Re-introduce authorization check with correct logic
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this order") # More specific error message
    return db_order

@router.get("/customer/me/", response_model=List[schemas.OrderSchema]) # GET /orders/customer/me/ to view current customer's orders
def read_customer_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: auth.TokenData = Depends(auth.get_current_user)):
    """
    Get a list of orders placed by the current customer (customer or admin - but only current customer's orders for customer).
    Supports pagination using skip and limit parameters.
    """
    user_id = auth.get_current_user_local_db(current_user, db).id
    orders = db.query(models.Order).filter(models.Order.user_id == user_id).offset(skip).limit(limit).all()
    return orders

@router.get("/admin/customer/{customer_id}/", response_model=List[schemas.OrderSchema]) # GET /orders/admin/customer/{customer_id}/ to view orders for a specific customer (admin only)
def read_orders_by_customer_admin(customer_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: auth.TokenData = Depends(auth.get_current_user)):
    """
    Get a list of orders placed by a specific customer (admin only).
    Accessible only to admin users.
    Supports pagination using skip and limit parameters.
    """
    if not auth.is_admin(current_user.roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    orders = db.query(models.Order).filter(models.Order.user_id == customer_id).offset(skip).limit(limit).all()
    return orders

@router.get("/", response_model=List[schemas.OrderSchema]) # GET /orders/ to view all orders (admin only) with pagination
def read_orders_all_admin(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: auth.TokenData = Depends(auth.get_current_user)):
    """
    Get a list of all orders (admin only), with pagination.
    Accessible only to admin users.
    """
    if not auth.is_admin(current_user.roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    orders = db.query(models.Order).offset(skip).limit(limit).all()
    return orders

@router.delete("/{order_id}", response_model=schemas.OrderSchema)
def delete_order(order_id: int, db: Session = Depends(get_db), current_user: auth.TokenData = Depends(auth.get_current_user)):
    """
    Delete a specific order by order ID (admin only).
    Accessible only to admin users.
    """
    if not auth.is_admin(current_user.roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    # Eagerly load order_line_items, their products, and the user relationship
    db_order = db.query(models.Order).options(
        joinedload(models.Order.order_line_items).joinedload(models.OrderLineItem.product),
        joinedload(models.Order.user)
    ).filter(models.Order.id == order_id).first()

    if not db_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    db.delete(db_order)
    db.commit()
    return db_order

class OrderStatusUpdate(BaseModel): # Request body for updating order status
    status: str # e.g., "pending", "processing", "shipped", "completed", "cancelled"

@router.put("/{order_id}/status/", response_model=schemas.OrderSchema) # PUT /orders/{order_id}/status/ to update order status (admin only)
def update_order_status(order_id: int, status_update: OrderStatusUpdate = Body(...), db: Session = Depends(get_db), current_user: auth.TokenData = Depends(auth.get_current_user)):
    """
    Update the status of a specific order (admin only).
    Accessible only to admin users.
    """
    if not auth.is_admin(current_user.roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    db_order.status = status_update.status # Update order status
    db.commit()
    db.refresh(db_order)
    return db_order