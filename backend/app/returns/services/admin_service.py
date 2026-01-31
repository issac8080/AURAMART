"""
AdminService: Handles manual review flow for functional damage returns.
"""
from sqlalchemy.orm import Session
from app.returns.db_models import Return
from app.returns.schemas import AdminDecision, ManualReviewItem, ManualReviewDetail
from app.returns.services.communication_agent import CommunicationAgent
from typing import List


class AdminService:
    """Service for admin manual review operations."""
    
    @staticmethod
    def get_pending_reviews(db: Session) -> List[ManualReviewItem]:
        """
        Get all return requests pending manual review.
        
        Args:
            db: Database session
            
        Returns:
            List of ManualReviewItem summaries
        """
        returns = db.query(Return).filter(
            Return.status == "MANUAL_REVIEW_PENDING"
        ).order_by(Return.created_at.desc()).all()
        
        items = []
        for return_obj in returns:
            order = return_obj.order
            items.append(ManualReviewItem(
                return_id=return_obj.id,
                order_id=return_obj.order_id,
                product_name=order.product_name,
                product_category=order.product_category,
                damage_type=return_obj.damage_type,
                description=return_obj.description[:200] + "..." if len(return_obj.description) > 200 else return_obj.description,
                status=return_obj.status,
                created_at=return_obj.created_at
            ))
        
        return items
    
    @staticmethod
    def get_review_detail(db: Session, return_id: int) -> ManualReviewDetail:
        """
        Get full details of a return request for admin review.
        
        Args:
            db: Database session
            return_id: Return request ID
            
        Returns:
            ManualReviewDetail with full information
        """
        return_obj = db.query(Return).filter(Return.id == return_id).first()
        if not return_obj:
            raise ValueError(f"Return request {return_id} not found")
        
        if return_obj.status != "MANUAL_REVIEW_PENDING":
            raise ValueError(f"Return request {return_id} is not pending review")
        
        return ManualReviewDetail.model_validate(return_obj)
    
    @staticmethod
    def submit_decision(
        db: Session,
        return_id: int,
        decision: AdminDecision
    ) -> Return:
        """
        Submit admin decision for a manual review.
        
        Args:
            db: Database session
            return_id: Return request ID
            decision: Admin decision and note
            
        Returns:
            Updated Return object
        """
        return_obj = db.query(Return).filter(Return.id == return_id).first()
        if not return_obj:
            raise ValueError(f"Return request {return_id} not found")
        
        if return_obj.status != "MANUAL_REVIEW_PENDING":
            raise ValueError(f"Return request {return_id} is not pending review")
        
        return_obj.admin_decision = decision.decision
        return_obj.admin_note = decision.note
        
        if decision.decision == "APPROVED":
            return_obj.status = "RETURN_APPROVED_MANUAL"
        else:
            return_obj.status = "RETURN_REJECTED_MANUAL"
        
        comm_output = CommunicationAgent.generate_message(
            admin_decision=decision.decision,
            admin_note=decision.note
        )
        
        db.flush()
        
        return return_obj
    
    @staticmethod
    def get_ai_approved_returns(db: Session) -> List[ManualReviewItem]:
        """
        Get all return requests approved by AI.
        
        Args:
            db: Database session
            
        Returns:
            List of ManualReviewItem summaries for AI-approved returns
        """
        returns = db.query(Return).filter(
            Return.status == "RETURN_APPROVED",
            Return.ai_decision == "APPROVED"
        ).order_by(Return.created_at.desc()).all()
        
        items = []
        for return_obj in returns:
            order = return_obj.order
            items.append(ManualReviewItem(
                return_id=return_obj.id,
                order_id=return_obj.order_id,
                product_name=order.product_name,
                product_category=order.product_category,
                damage_type=return_obj.damage_type,
                description=return_obj.description[:200] + "..." if len(return_obj.description) > 200 else return_obj.description,
                status=return_obj.status,
                created_at=return_obj.created_at
            ))
        
        return items
    
    @staticmethod
    def get_ai_rejected_returns(db: Session) -> List[ManualReviewItem]:
        """
        Get all return requests rejected by AI.
        
        Args:
            db: Database session
            
        Returns:
            List of ManualReviewItem summaries for AI-rejected returns
        """
        returns = db.query(Return).filter(
            Return.status == "RETURN_REJECTED",
            Return.ai_decision == "REJECTED"
        ).order_by(Return.created_at.desc()).all()
        
        items = []
        for return_obj in returns:
            order = return_obj.order
            items.append(ManualReviewItem(
                return_id=return_obj.id,
                order_id=return_obj.order_id,
                product_name=order.product_name,
                product_category=order.product_category,
                damage_type=return_obj.damage_type,
                description=return_obj.description[:200] + "..." if len(return_obj.description) > 200 else return_obj.description,
                status=return_obj.status,
                created_at=return_obj.created_at
            ))
        
        return items
    
    @staticmethod
    def get_ai_decision_detail(db: Session, return_id: int) -> ManualReviewDetail:
        """
        Get full details of an AI-processed return request.
        
        Args:
            db: Database session
            return_id: Return request ID
            
        Returns:
            ManualReviewDetail with full information including AI decision
        """
        return_obj = db.query(Return).filter(Return.id == return_id).first()
        if not return_obj:
            raise ValueError(f"Return request {return_id} not found")
        
        if return_obj.status not in ["RETURN_APPROVED", "RETURN_REJECTED"]:
            raise ValueError(f"Return request {return_id} is not an AI-processed return")
        
        return ManualReviewDetail.model_validate(return_obj)
    
    @staticmethod
    def get_manual_review_history(db: Session) -> List[ManualReviewItem]:
        """
        Get all return requests that have been manually reviewed (completed reviews).
        
        Args:
            db: Database session
            
        Returns:
            List of ManualReviewItem summaries for manually reviewed returns
        """
        returns = db.query(Return).filter(
            Return.status.in_(["RETURN_APPROVED_MANUAL", "RETURN_REJECTED_MANUAL"]),
            Return.admin_decision.isnot(None)
        ).order_by(Return.updated_at.desc()).all()
        
        items = []
        for return_obj in returns:
            order = return_obj.order
            items.append(ManualReviewItem(
                return_id=return_obj.id,
                order_id=return_obj.order_id,
                product_name=order.product_name,
                product_category=order.product_category,
                damage_type=return_obj.damage_type,
                description=return_obj.description[:200] + "..." if len(return_obj.description) > 200 else return_obj.description,
                status=return_obj.status,
                created_at=return_obj.created_at
            ))
        
        return items
    
    @staticmethod
    def get_manual_review_detail(db: Session, return_id: int) -> ManualReviewDetail:
        """
        Get full details of a manually reviewed return request (for history view).
        
        Args:
            db: Database session
            return_id: Return request ID
            
        Returns:
            ManualReviewDetail with full information including admin decision
        """
        return_obj = db.query(Return).filter(Return.id == return_id).first()
        if not return_obj:
            raise ValueError(f"Return request {return_id} not found")
        
        if return_obj.status not in ["RETURN_APPROVED_MANUAL", "RETURN_REJECTED_MANUAL"]:
            raise ValueError(f"Return request {return_id} is not a manually reviewed return")
        
        return ManualReviewDetail.model_validate(return_obj)

