"""
ReturnsService: Orchestrates the agent pipeline for processing return requests.
Uses LangGraph for workflow orchestration.
"""
import json
from sqlalchemy.orm import Session
from app.returns.db_models import Return, Order
from app.returns.schemas import ReturnCreate, ReturnResponse
from app.returns.services.returns_workflow import returns_workflow, ReturnProcessingState
from app.returns.config import settings

# Import OPIK tracking if available
try:
    from opik import track
    OPIK_AVAILABLE = True
except ImportError:
    OPIK_AVAILABLE = False
    # Create a no-op decorator if OPIK is not available
    def track(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


class ReturnsService:
    """Service for orchestrating return request processing."""
    
    @staticmethod
    def process_return_request(
        db: Session,
        return_data: ReturnCreate
    ) -> Return:
        """
        Process a return request through the agent pipeline.
        
        Flow:
        1. Validate order and category
        2. Route based on damage type:
           - FUNCTIONAL (Electronics only) → Manual review
           - PHYSICAL → AI pipeline (VisionAgent → PolicyAgent → ResolutionAgent → CommunicationAgent)
        3. Store result in database
        
        Args:
            db: Database session
            return_data: Return request data
            
        Returns:
            Created Return object
        """
        order = db.query(Order).filter(Order.order_id == return_data.order_id).first()
        if not order:
            raise ValueError(f"Order {return_data.order_id} not found")
        
        if order.product_category != return_data.category:
            raise ValueError(
                f"Category mismatch: order category is {order.product_category}, "
                f"but request category is {return_data.category}"
            )
        
        if return_data.damage_type == "FUNCTIONAL" and return_data.category != "Electronics":
            raise ValueError("Functional damage is only available for Electronics category")
        
        if return_data.damage_type == "FUNCTIONAL":
            return_obj = ReturnsService._create_manual_review_return(
                db, return_data, order
            )
        else:
            return_obj = ReturnsService._process_ai_return(
                db, return_data, order
            )
        
        return return_obj
    
    @staticmethod
    def _serialize_media(return_data: ReturnCreate) -> str:
        """Serialize media files to JSON string."""
        if return_data.media_base64:
            return json.dumps([{
                "data": m.data,
                "mime_type": m.mime_type,
                "filename": m.filename
            } for m in return_data.media_base64])
        elif return_data.media_files:
            return json.dumps(return_data.media_files)
        return None
    
    @staticmethod
    def _create_manual_review_return(
        db: Session,
        return_data: ReturnCreate,
        order: Order
    ) -> Return:
        """Create a return request that requires manual review."""
        media_data = ReturnsService._serialize_media(return_data)
        
        return_obj = Return(
            order_id=return_data.order_id,
            damage_type=return_data.damage_type,
            description=return_data.description,
            status="MANUAL_REVIEW_PENDING",
            media_files=media_data,
            customer_email=return_data.customer_email,
            customer_phone=return_data.customer_phone
        )
        
        db.add(return_obj)
        db.flush()
        
        return return_obj
    
    @staticmethod
    @track(name="process_ai_return", type="general", project_name=settings.opik_project_name if OPIK_AVAILABLE else None, flush=True)
    def _process_ai_return(
        db: Session,
        return_data: ReturnCreate,
        order: Order
    ) -> Return:
        """Process physical damage return through AI agent pipeline using LangGraph."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[ReturnsService] Starting workflow for order {return_data.order_id}")
        
        initial_state: ReturnProcessingState = {
            "return_data": return_data,
            "order_id": return_data.order_id,
            "purchase_date": order.purchase_date,
            "product_name": order.product_name,
            "product_category": order.product_category,
            "vision_output": None,
            "policy_output": None,
            "resolution_output": None,
            "communication_output": None,
            "description_similarity": None,
            "probable_cause": None,
            "decision_type": None,
            "escalation_reason": None,
            "status": "PROCESSING",
            "ai_decision": None,
            "ai_confidence": None,
            "ai_reason": None,
            "vision_agent_output_json": None,
            "policy_agent_output_json": None,
            "error": None,
            "step": "start"
        }
        
        try:
            final_state = returns_workflow.invoke(initial_state)
            
            status = final_state.get("status", "RETURN_REJECTED")
            
            if final_state.get("error") and status not in ["RETURN_REJECTED", "RETURN_APPROVED", "MANUAL_REVIEW_PENDING"]:
                logger.error(f"[ReturnsService] Workflow error for order {return_data.order_id}: {final_state['error']}")
                raise ValueError(f"Workflow error: {final_state['error']}")
            ai_decision = final_state.get("ai_decision")
            decision_type = final_state.get("decision_type") or ai_decision
            ai_confidence = final_state.get("ai_confidence")
            ai_reason = final_state.get("ai_reason")
            probable_cause = final_state.get("probable_cause")
            escalation_reason = final_state.get("escalation_reason")
            vision_agent_output_json = final_state.get("vision_agent_output_json")
            policy_agent_output_json = final_state.get("policy_agent_output_json")
            
            logger.info(f"[ReturnsService] Results - Status: {status}, Decision: {decision_type}, Confidence: {ai_confidence:.2%}")
            
            media_data = ReturnsService._serialize_media(return_data)
            
            return_obj = Return(
                order_id=return_data.order_id,
                damage_type=return_data.damage_type,
                description=return_data.description,
                status=status,
                ai_decision=decision_type,
                ai_confidence=ai_confidence,
                ai_reason=ai_reason,
                probable_cause=probable_cause,
                decision_type=decision_type,
                escalation_reason=escalation_reason,
                media_files=media_data,
                vision_agent_output=vision_agent_output_json,
                policy_agent_output=policy_agent_output_json,
                customer_email=return_data.customer_email,
                customer_phone=return_data.customer_phone
            )
            
            db.add(return_obj)
            db.flush()
            
            # Flush OPIK traces to ensure they're sent immediately
            if OPIK_AVAILABLE:
                try:
                    import opik
                    opik.flush_tracker()
                    logger.info(f"[ReturnsService] OPIK traces flushed for order {return_data.order_id}")
                except Exception as flush_error:
                    logger.warning(f"[ReturnsService] Failed to flush OPIK traces: {str(flush_error)}")
            
            return return_obj
            
        except Exception as e:
            logger.error(f"[ReturnsService] Workflow failed for order {return_data.order_id}: {str(e)}", exc_info=True)
            raise ValueError(f"Error processing return request: {str(e)}")
    
    @staticmethod
    def get_return_by_order_id(db: Session, order_id: str) -> Return:
        """Get the most recent return request for an order."""
        return db.query(Return).filter(
            Return.order_id == order_id
        ).order_by(Return.created_at.desc()).first()
    
    @staticmethod
    def get_return_by_id(db: Session, return_id: int) -> Return:
        """Get a return request by its ID."""
        return db.query(Return).filter(Return.id == return_id).first()

