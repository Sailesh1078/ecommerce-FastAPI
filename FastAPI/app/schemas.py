# app/schemas.py

from pydantic import BaseModel, EmailStr
from typing import List, Optional

# ---------------------------
# User Schemas
# ---------------------------
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    role: str

    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None

    class Config:
        orm_mode = True

# ---------------------------
# Category Schemas
# ---------------------------
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryOut(CategoryBase):
    id: int

    class Config:
        orm_mode = True

# ---------------------------
# Product Schemas
# ---------------------------
class ProductBase(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    image_url: Optional[str] = None
    count: Optional[int] = 1  # Default value if not provided
    # A product must belong to a category.
    category_id: int

class ProductCreate(ProductBase):
    pass

class ProductOut(ProductBase):
    id: int

    class Config:
        orm_mode = True

# ---------------------------
# Order Item Schemas
# ---------------------------
class OrderItemBase(BaseModel):
    product_id: int
    quantity: int = 1

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemOut(OrderItemBase):
    id: int
    product: ProductOut

    class Config:
        orm_mode = True

# ---------------------------
# Order Schemas
# ---------------------------
class OrderBase(BaseModel):
    pass

class OrderCreate(OrderBase):
    order_items: List[OrderItemCreate]

class OrderOut(OrderBase):
    id: int
    user_id: int
    ## order_items: List[OrderItemOut]

    class Config:
        orm_mode = True
