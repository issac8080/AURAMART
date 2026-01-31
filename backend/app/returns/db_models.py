"""
SQLAlchemy ORM models for the IntelliReturn system.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Order(Base):
    """Order model storing customer order information."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True, nullable=False)
    customer_id = Column(String, nullable=False, default="user_001")
    product_name = Column(String, nullable=False)
    product_category = Column(String, nullable=False)
    purchase_date = Column(DateTime, nullable=False)
    status = Column(String, nullable=False, default="delivered")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    returns = relationship("Return", back_populates="order")


class Policy(Base):
    """Policy model storing return policy clauses."""
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(String, unique=True, index=True, nullable=False)
    product_category = Column(String, nullable=True)
    title = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Return(Base):
    """Return request model storing return information and AI/admin decisions."""
    __tablename__ = "returns"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("orders.order_id"), nullable=False, index=True)
    damage_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, nullable=False)
    
    # Customer contact info (replaces authentication)
    customer_email = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    
    ai_decision = Column(String, nullable=True)
    ai_confidence = Column(Float, nullable=True)
    ai_reason = Column(Text, nullable=True)
    
    probable_cause = Column(String, nullable=True)
    decision_type = Column(String, nullable=True)
    escalation_reason = Column(Text, nullable=True)
    
    admin_decision = Column(String, nullable=True)
    admin_note = Column(Text, nullable=True)
    
    media_files = Column(Text, nullable=True)
    
    vision_agent_output = Column(Text, nullable=True)
    policy_agent_output = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = relationship("Order", back_populates="returns")
