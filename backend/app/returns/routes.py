"""
Return & Exchange API Routes (Authentication Removed)
Autonomous operation - works with Order ID, Product ID, and customer contact info
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.returns.db import get_db
from app.returns.schemas import (
    ReturnCreate,
    ReturnResponse,
    ReturnWithOrder,
)
from app.returns.services.returns_service import ReturnsService
from app.returns.db_models import Return, Order

router = APIRouter(prefix="/api/returns", tags=["returns"])


@router.post("/", response_model=ReturnResponse, status_code=status.HTTP_201_CREATED)
async def create_return_request(
    return_data: ReturnCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new return request (No Authentication Required)
    
    Works autonomously with:
    - Order ID
    - Product ID/SKU
    - Customer contact info (email/phone)
    
    Flow:
    - FUNCTIONAL damage (Electronics only) → Manual review
    - PHYSICAL damage → AI pipeline (VisionAgent → PolicyAgent → ResolutionAgent)
    
    Args:
        return_data: Return request data
        db: Database session
    """
    try:
        return_obj = ReturnsService.process_return_request(db, return_data)
        db.commit()
        db.refresh(return_obj)
        return return_obj
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing return request: {str(e)}"
        )


@router.get("/order/{order_id}", response_model=ReturnWithOrder)
async def get_return_by_order_id(
    order_id: str,
    db: Session = Depends(get_db)
):
    """
    Get return request details for an order (No Authentication Required)
    
    Args:
        order_id: Order ID from AuraShop
        db: Database session
    """
    return_obj = ReturnsService.get_return_by_order_id(db, order_id)
    if not return_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No return request found for order {order_id}"
        )
    
    return_obj.order = db.query(Order).filter(Order.order_id == order_id).first()
    return return_obj


@router.get("/{return_id}", response_model=ReturnResponse)
async def get_return_by_id(
    return_id: int,
    db: Session = Depends(get_db)
):
    """
    Get return request by ID (No Authentication Required)
    
    Args:
        return_id: Return request ID
        db: Database session
    """
    return_obj = db.query(Return).filter(Return.id == return_id).first()
    if not return_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return request {return_id} not found"
        )
    return return_obj


@router.get("/", response_model=List[ReturnResponse])
async def get_all_returns(
    order_id: str = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    """
    Get all return requests with optional filters (No Authentication Required)
    
    Args:
        order_id: Optional filter by order ID
        status: Optional filter by status
        db: Database session
    """
    query = db.query(Return)
    
    if order_id:
        query = query.filter(Return.order_id == order_id)
    if status:
        query = query.filter(Return.status == status)
    
    returns = query.order_by(Return.created_at.desc()).all()
    return returns
