# models.py
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime, Table, Enum
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import enum # Import the enum module

# --- Define Order Status Enum ---
class OrderStatus(str, enum.Enum): # Use enum.Enum
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

# Association table for User and Role (Many-to-Many)
user_role_association = Table(
    "user_role",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("role_id", Integer, ForeignKey("roles.id")),
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True)
    first_name = Column(String)  # Kept as first_name and last_name
    last_name = Column(String)
    is_active = Column(Boolean, default=True)

    roles = relationship("Role", secondary=user_role_association, backref="users")
    orders = relationship("Order", back_populates="user")
    favorite_products = relationship("FavoriteProduct", back_populates="user", cascade="all, delete-orphan") # Corrected back_populates to "user"
    cart_items = relationship("OrderItem", back_populates="user_cart", foreign_keys="OrderItem.user_id") # Relationship for user's cart items

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, default=0)
    category_id = Column(Integer, ForeignKey("categories.id"))
    image_url = Column(String) # Added image_url

    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product") # Keep OrderItem relationship for cart
    favorite_products = relationship("FavoriteProduct", back_populates="product", cascade="all, delete-orphan") # Corrected back_populates to "product"
    order_line_items = relationship("OrderLineItem", back_populates="product") # Relationship with OrderLineItem

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    order_date = Column(DateTime, default=datetime.utcnow) # Keep default=datetime.utcnow
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING) # Use Enum and set default status

    user = relationship("User", back_populates="orders")
    order_line_items = relationship("OrderLineItem", back_populates="order",  cascade="all, delete-orphan") # Relationship with OrderLineItem, renamed from order_items

class OrderItem(Base): # OrderItem now represents CART ITEM
    __tablename__ = "order_items" # Keep table name as order_items for cart

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # Keep user_id for cart association
    product_id = Column(Integer, ForeignKey("products.id")) # Foreign Key to Product
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False) # Price at the time of cart addition

    user_cart = relationship("User", back_populates="cart_items", foreign_keys=[user_id]) # Relationship for user's cart items
    product = relationship("Product", back_populates="order_items") # Keep product relationship for cart


class OrderLineItem(Base): # New model for ORDER LINE ITEMS
    __tablename__ = "order_line_items" # New table for order line items

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False) # Foreign Key to Order (NOT NULL)
    product_id = Column(Integer, ForeignKey("products.id")) # Foreign Key to Product
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False) # Price at the time of order

    order = relationship("Order", back_populates="order_line_items") # Relationship with Order
    product = relationship("Product", back_populates="order_line_items") # Relationship with Product


class FavoriteProduct(Base):
    __tablename__ = "favorite_products"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))

    user = relationship("User", back_populates="favorite_products") # Corrected back_populates to "favorite_products"
    product = relationship("Product", back_populates="favorite_products") # Corrected back_populates to "favorite_products"