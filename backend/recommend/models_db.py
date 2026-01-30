"""
SQLAlchemy ORM models for recommendation and chatbot.
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    user_id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="user", foreign_keys="Order.user_id")


class Product(Base):
    __tablename__ = "products"
    id = Column(String(32), primary_key=True)
    name = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    currency = Column(String(8), default="INR")
    category = Column(String(128), nullable=True)
    subcategory = Column(String(128), nullable=True)
    brand = Column(String(128), nullable=True)
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    colors = Column(JSON, default=list)  # ["Red", "Navy"]
    sizes = Column(JSON, default=list)
    image_url = Column(String(1024), nullable=True)
    tags = Column(JSON, default=list)
    in_stock = Column(Boolean, default=True)
    stock_count = Column(Integer, nullable=True)
    restock_estimate_days = Column(Integer, nullable=True)  # probable restock in days

    order_items = relationship("OrderItem", back_populates="product")


class Order(Base):
    __tablename__ = "orders"
    id = Column(String(32), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False)
    total = Column(Float, nullable=False)
    delivery_method = Column(String(32), nullable=False)  # home_delivery, store_pickup
    status = Column(String(32), nullable=False)
    delivery_address = Column(Text, nullable=True)
    store_location = Column(String(128), nullable=True)
    qr_code = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(32), ForeignKey("orders.id"), nullable=False)
    product_id = Column(String(32), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(128), nullable=False)
    user_id = Column(String(64), nullable=True)
    event_type = Column(String(64), nullable=False)
    product_id = Column(String(32), nullable=True)
    category = Column(String(128), nullable=True)
    query = Column(String(512), nullable=True)
    amount = Column(Float, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Cart(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=True)
    session_id = Column(String(128), nullable=True)
    product_id = Column(String(32), nullable=False)
    quantity = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StockNotify(Base):
    __tablename__ = "stock_notify"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False)
    product_id = Column(String(32), nullable=False)
    notified = Column(Boolean, default=False)
    probable_restock_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Festival(Base):
    __tablename__ = "festivals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    suggested_categories = Column(JSON, default=list)  # ["Clothing", "Electronics"]
    description = Column(Text, nullable=True)


class FAQ(Base):
    __tablename__ = "faq"
    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(64), nullable=True)
