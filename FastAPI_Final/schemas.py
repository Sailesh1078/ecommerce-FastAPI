# schemas.py
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class RoleSchema(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True

class UserSchema(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool
    roles: List[RoleSchema]
    first_name: Optional[str] = None # Kept as first_name and last_name
    last_name: Optional[str] = None
    created_at: Optional[datetime] = None # Added created_at

    class Config:
        orm_mode = True

class UserCreate(BaseModel): # Renamed from UserCreateSchema and adjusted fields
    username: str
    email: EmailStr
    first_name: str # Kept as first_name and last_name
    last_name: str
    password: str # Keep password for internal schema, but not used in DB model


class UserUpdate(BaseModel): # Renamed from UserUpdateSchema
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    first_name: Optional[str] = None # Kept as first_name and last_name
    last_name: Optional[str] = None
    password: Optional[str] = None # Keep password for internal schema, but not used in DB model


class UserDelete(BaseModel):
    username: str

class CategorySchema(BaseModel):
    id: int
    name: str
    product_count: int = 0 # Added product_count

    class Config:
        orm_mode = True

class CategoryCreateSchema(BaseModel):
    name: str

class CategoryUpdateSchema(BaseModel):
    name: Optional[str] = None

class ProductSchema(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    quantity: int
    category: CategorySchema
    image_url: Optional[str] = None # Added image_url

    class Config:
        orm_mode = True

class ProductCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    quantity: int
    category_id: int
    image_url: Optional[str] = None # Added image_url

class ProductUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    category_id: Optional[int] = None
    image_url: Optional[str] = None # Added image_url

# --- Order Item Schemas (CART ITEM) ---
class OrderItemCreate(BaseModel): # Renamed from OrderItemCreateSchema
    product_id: int
    quantity: int

class OrderItemSchema(BaseModel): # Renamed from OrderItemSchema
    id: int
    product_id: int
    quantity: int
    order_id: Optional[int] = None # order_id is optional for cart items
    user_id: int # <---- ADDED user_id to schema
    product: ProductSchema

    class Config:
        orm_mode = True

# --- Order Line Item Schemas (NEW for ORDERED ITEMS) ---
class OrderLineItemSchema(BaseModel): # New Schema for OrderLineItem
    id: int
    product_id: int
    quantity: int
    order_id: int # order_id is NOT optional here
    product: ProductSchema

    class Config:
        orm_mode = True


# --- Order Schemas ---
class OrderCreate(BaseModel): # Renamed from OrderCreateSchema
    pass # OrderCreate will be empty now, as order items are not sent in request body

class OrderSchema(BaseModel): # Renamed from OrderSchema
    id: int
    user_id: int # Added user_id
    order_date: datetime
    status: str # Added status
    order_line_items: List[OrderLineItemSchema] # Use OrderLineItemSchema here, renamed from order_items

    user: UserSchema # Include user details (relationship)

    class Config:
        orm_mode = True


class FavoriteProductSchema(BaseModel):
    id: int
    product: ProductSchema

    class Config:
        orm_mode = True

class FavoriteProductCreateSchema(BaseModel):
    product_id: int

# --- Response Schemas for Lists with Pagination ---
class CategoryListResponse(BaseModel):
    items: List[CategorySchema]
    total: int
    skip: int
    limit: int

class ProductListResponse(BaseModel):
    items: List[ProductSchema]
    total: int
    skip: int
    limit: int
    category_id_filter: Optional[int] = None # To reflect applied filters
    search_query: Optional[str] = None # To reflect applied search query

# --- Registration Request Schemas  ---
class CustomerRegistrationRequest(BaseModel):
    username: str
    password: str
    email: EmailStr
    firstName: str # Kept as firstName and lastName
    lastName: str

class AdminRegistrationRequest(BaseModel):
    username: str
    password: str
    email: EmailStr
    firstName: str # Kept as firstName and lastName
    lastName: str

# --- Keycloak Token Schema ---
class KeycloakToken(BaseModel):
    username: str
    roles: List[str]