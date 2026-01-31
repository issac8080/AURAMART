"""
LangGraph workflow for orchestrating return request processing.
"""
import logging
from typing import TypedDict, Literal, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from app.returns.schemas import (
    VisionAgentOutput,
    PolicyAgentOutput,
    ResolutionAgentOutput,
    CommunicationAgentOutput,
    ReturnCreate
)
from app.returns.services.vision_agent import VisionAgent
from app.returns.services.policy_agent import PolicyAgent
from app.returns.services.resolution_agent import ResolutionAgent
from app.returns.services.communication_agent import CommunicationAgent
from app.returns.services.embedding_service import embedding_service
from app.returns.config import settings

# Set up logger
logger = logging.getLogger(__name__)


class ReturnProcessingState(TypedDict, total=False):
    """State for the return processing workflow."""
    return_data: ReturnCreate
    order_id: str
    purchase_date: datetime
    product_name: Optional[str]
    product_category: Optional[str]
    
    vision_output: Optional[VisionAgentOutput]
    policy_output: Optional[PolicyAgentOutput]
    resolution_output: Optional[ResolutionAgentOutput]
    communication_output: Optional[CommunicationAgentOutput]
    
    description_similarity: Optional[float]
    probable_cause: Optional[str]
    decision_type: Optional[str]
    escalation_reason: Optional[str]
    
    status: str
    ai_decision: Optional[str]
    ai_confidence: Optional[float]
    ai_reason: Optional[str]
    vision_agent_output_json: Optional[str]
    policy_agent_output_json: Optional[str]
    
    error: Optional[str]
    step: str


def vision_node(state: ReturnProcessingState) -> ReturnProcessingState:
    """VisionAgent node: Analyze defect from images and description."""
    order_id = state.get("order_id", "unknown")
    logger.info(f"[LangGraph Workflow] Starting VisionAgent node for order {order_id}")
    
    try:
        return_data = state["return_data"]
        logger.info(f"[VisionAgent] Processing return for order {order_id}, category: {return_data.category}, damage_type: {return_data.damage_type}")
        logger.info(f"[VisionAgent] Description: {return_data.description[:100]}...")
        
        media_base64_dicts = None
        if return_data.media_base64:
            media_base64_dicts = [
                {"data": media.data, "mime_type": media.mime_type}
                for media in return_data.media_base64
            ]
            logger.info(f"[VisionAgent] Processing {len(media_base64_dicts)} media file(s) for analysis")
        
        logger.info(f"[VisionAgent] Calling VisionAgent.analyze_defect() - may use GPT-4o Vision API")
        product_name = state.get("product_name")
        vision_output = VisionAgent.analyze_defect(
            description=return_data.description,
            damage_type=return_data.damage_type,
            category=return_data.category,
            media_files=return_data.media_files,
            media_base64=media_base64_dicts,
            product_name=product_name
        )
        
        logger.info(f"[VisionAgent] Analysis complete - Defect: {vision_output.defect_label}, Severity: {vision_output.estimated_severity}, Probable cause: {vision_output.probable_cause}")
        
        if vision_output.defect_label == "image_mismatch" or "VALIDATION_FAILED" in (vision_output.damage_pattern_analysis or ""):
            validation_error = vision_output.damage_pattern_analysis or vision_output.defect_location or "Image does not match the product or description"
            if "VALIDATION_FAILED:" in validation_error:
                validation_error = validation_error.replace("VALIDATION_FAILED:", "").strip()
            
            logger.info(f"[LangGraph Workflow] Image validation failed for order {order_id} - This is a valid rejection decision: {validation_error}")
            
            # Create a rejection reason
            rejection_reason = (
                f"{validation_error}. "
                f"Please ensure the images you upload match the product you ordered and accurately show the damage you described. "
                f"If you believe this is an error, please contact our support team with additional information."
            )
            
            # Generate communication message for the rejection
            from app.services.communication_agent import CommunicationAgent
            from app.schemas import ResolutionAgentOutput
            
            # Create a mock resolution output for the rejection
            mock_resolution = ResolutionAgentOutput(
                decision="REJECTED",
                confidence=0.0,
                reason=rejection_reason,
                decision_type="REJECTED",
                escalation_reason=None
            )
            
            comm_output = CommunicationAgent.generate_message(
                resolution_output=mock_resolution,
                product_name=state.get("product_name"),
                product_category=state.get("product_category"),
                user_description=state.get("return_data", {}).description if state.get("return_data") else None
            )
            
            # Return state with rejection - NO error field, this is a valid AI decision
            # Confidence is 1.0 (100%) because we're CERTAIN there's a mismatch
            return {
                **state,
                "status": "RETURN_REJECTED",
                "ai_decision": "REJECTED",
                "decision_type": "REJECTED",
                "ai_confidence": 1.0,  # 100% confidence - we're certain the image doesn't match
                "ai_reason": comm_output.user_message_body,  # Use communication agent's message
                "communication_output": comm_output,
                "vision_output": vision_output,  # Keep vision output for reference
                "step": "vision_validation_failed"
            }
        
        return {
            **state,
            "vision_output": vision_output,
            "probable_cause": vision_output.probable_cause,
            "vision_agent_output_json": VisionAgent.to_json(vision_output),
            "step": "vision_complete"
        }
    except Exception as e:
        logger.error(f"[LangGraph Workflow] VisionAgent node failed for order {order_id}: {str(e)}", exc_info=True)
        return {
            **state,
            "error": f"VisionAgent error: {str(e)}",
            "step": "vision_error"
        }


def policy_node(state: ReturnProcessingState) -> ReturnProcessingState:
    """PolicyAgent node: Match defect with policy clauses using RAG."""
    order_id = state.get("order_id", "unknown")
    logger.info(f"[LangGraph Workflow] Starting PolicyAgent node for order {order_id}")
    
    try:
        if state.get("error"):
            logger.warning(f"[PolicyAgent] Skipping due to previous error: {state.get('error')}")
            return state
        
        vision_output = state["vision_output"]
        if not vision_output:
            logger.error(f"[PolicyAgent] VisionAgent output missing for order {order_id}")
            return {
                **state,
                "error": "VisionAgent output is required for PolicyAgent",
                "step": "policy_error"
            }
        
        return_data = state["return_data"]
        logger.info(f"[PolicyAgent] Matching policies for category: {return_data.category}")
        logger.info(f"[PolicyAgent] Using VisionAgent output - Defect: {vision_output.defect_label}, Severity: {vision_output.estimated_severity}")
        logger.info(f"[PolicyAgent] Calling PolicyAgent.match_policy() - will use RAG (ChromaDB) and may use GPT-4o for interpretation")
        
        policy_output = PolicyAgent.match_policy(
            description=return_data.description,
            vision_output=vision_output,
            product_category=return_data.category
        )
        
        logger.info(f"[PolicyAgent] Policy matching complete - Confidence: {policy_output.confidence:.2%}, Matched {len(policy_output.matched_policy_ids)} policies")
        
        return {
            **state,
            "policy_output": policy_output,
            "policy_agent_output_json": PolicyAgent.to_json(policy_output),
            "step": "policy_complete"
        }
    except Exception as e:
        logger.error(f"[LangGraph Workflow] PolicyAgent node failed for order {order_id}: {str(e)}", exc_info=True)
        return {
            **state,
            "error": f"PolicyAgent error: {str(e)}",
            "step": "policy_error"
        }


def resolution_node(state: ReturnProcessingState) -> ReturnProcessingState:
    """ResolutionAgent node: Make final decision based on policy and rules."""
    order_id = state.get("order_id", "unknown")
    logger.info(f"[LangGraph Workflow] Starting ResolutionAgent node for order {order_id}")
    
    try:
        if state.get("error"):
            logger.warning(f"[ResolutionAgent] Skipping due to previous error: {state.get('error')}")
            return state
        
        policy_output = state["policy_output"]
        if not policy_output:
            logger.error(f"[ResolutionAgent] PolicyAgent output missing for order {order_id}")
            return {
                **state,
                "error": "PolicyAgent output is required for ResolutionAgent",
                "step": "resolution_error"
            }
        
        return_data = state["return_data"]
        purchase_date = state["purchase_date"]
        
        # Get vision output for full context (including probable_cause)
        vision_output = state.get("vision_output")
        vision_confidence = vision_output.vision_confidence if vision_output else None
        description_similarity = state.get("description_similarity")
        
        logger.info(f"[ResolutionAgent] Making decision - Policy Confidence: {policy_output.confidence:.2%}, Purchase date: {purchase_date}")
        if vision_output:
            logger.info(f"[ResolutionAgent] Vision output available - Probable cause: {vision_output.probable_cause}, Severity: {vision_output.estimated_severity}")
        if vision_confidence is not None:
            logger.info(f"[ResolutionAgent] Vision confidence: {vision_confidence:.2%}")
        if description_similarity is not None:
            logger.info(f"[ResolutionAgent] Description similarity: {description_similarity:.2%}")
        logger.info(f"[ResolutionAgent] Calling ResolutionAgent.resolve() - applying business rules with combined confidence")
        
        resolution_output = ResolutionAgent.resolve(
            policy_output=policy_output,
            damage_type=return_data.damage_type,
            purchase_date=purchase_date,
            vision_output=vision_output,  # Pass full vision_output for probable_cause and other details
            vision_confidence=vision_confidence,
            description_similarity=description_similarity
        )
        
        # Map decision to status with enhanced routing
        # Note: ESCALATE_TO_HUMAN maps to MANUAL_REVIEW_PENDING (they're the same thing)
        decision = resolution_output.decision
        if decision == "APPROVED":
            status = "RETURN_APPROVED"
        elif decision == "REJECTED":
            status = "RETURN_REJECTED"
        elif decision == "ESCALATE_TO_HUMAN":
            status = "MANUAL_REVIEW_PENDING"
        else:
            status = "RETURN_REJECTED"  # Default fallback
        
        # Extract escalation reason if applicable
        escalation_reason = None
        if decision == "ESCALATE_TO_HUMAN":
            escalation_reason = resolution_output.reason
        
        logger.info(f"[ResolutionAgent] Decision: {decision} (Confidence: {resolution_output.confidence:.2%}), Status: {status}")
        
        return {
            **state,
            "resolution_output": resolution_output,
            "status": status,
            "ai_decision": decision,
            "decision_type": decision,
            "ai_confidence": resolution_output.confidence,
            "escalation_reason": escalation_reason,
            "step": "resolution_complete"
        }
    except Exception as e:
        logger.error(f"[LangGraph Workflow] ResolutionAgent node failed for order {order_id}: {str(e)}", exc_info=True)
        return {
            **state,
            "error": f"ResolutionAgent error: {str(e)}",
            "step": "resolution_error"
        }


def communication_node(state: ReturnProcessingState) -> ReturnProcessingState:
    """CommunicationAgent node: Generate user-friendly message."""
    order_id = state.get("order_id", "unknown")
    logger.info(f"[LangGraph Workflow] Starting CommunicationAgent node for order {order_id}")
    
    try:
        # Check if communication output is already generated (e.g., from image validation failure)
        if state.get("communication_output"):
            logger.info(f"[CommunicationAgent] Using pre-generated communication output for order {order_id}")
            return {
                **state,
                "step": "complete"
            }
        
        if state.get("error"):
            logger.warning(f"[CommunicationAgent] Skipping due to previous error: {state.get('error')}")
            return state
        
        resolution_output = state.get("resolution_output")
        if not resolution_output:
            logger.error(f"[CommunicationAgent] ResolutionAgent output missing for order {order_id}")
            return {
                **state,
                "error": "ResolutionAgent output is required for CommunicationAgent",
                "step": "communication_error"
            }
        
        logger.info(f"[CommunicationAgent] Generating user message for decision: {resolution_output.decision}")
        logger.info(f"[CommunicationAgent] Calling CommunicationAgent.generate_message() - may use GPT-4o for message generation")
        
        # Get product information from state
        product_name = state.get("product_name")
        product_category = state.get("product_category")
        user_description = state.get("return_data", {}).description if state.get("return_data") else None
        
        comm_output = CommunicationAgent.generate_message(
            resolution_output=resolution_output,
            product_name=product_name,
            product_category=product_category,
            user_description=user_description
        )
        
        logger.info(f"[LangGraph Workflow] Workflow completed for order {order_id} - Status: {state.get('status')}")
        
        return {
            **state,
            "communication_output": comm_output,
            "ai_reason": comm_output.user_message_body,
            "step": "complete"
        }
    except Exception as e:
        logger.error(f"[LangGraph Workflow] CommunicationAgent node failed for order {order_id}: {str(e)}", exc_info=True)
        return {
            **state,
            "error": f"CommunicationAgent error: {str(e)}",
            "step": "communication_error"
        }


def description_comparison_node(state: ReturnProcessingState) -> ReturnProcessingState:
    """Compare OpenAI-generated image description with user description using embedding similarity."""
    order_id = state.get("order_id", "unknown")
    logger.info(f"[LangGraph] Starting Description Comparison for order {order_id}")
    
    try:
        if state.get("error"):
            logger.warning(f"[Description Comparison] Skipping due to previous error: {state.get('error')}")
            return state
        
        vision_output = state["vision_output"]
        return_data = state["return_data"]
        
        if not vision_output or not vision_output.image_description:
            logger.warning(f"[Description Comparison] Vision output or image description missing for order {order_id}")
            return {
                **state,
                "description_similarity": None,
                "step": "description_comparison_skipped"
            }
        
        user_description = return_data.description
        openai_description = vision_output.image_description
        
        # Use embedding similarity only (no GPT-4o)
        user_embedding = embedding_service.embed_text(user_description)
        openai_embedding = embedding_service.embed_text(openai_description)
        similarity = embedding_service.cosine_similarity(user_embedding, openai_embedding)
        similarity = max(0.0, min(1.0, similarity))
        
        logger.info(f"[Description Comparison] Similarity: {similarity:.2%}")
        
        return {
            **state,
            "description_similarity": similarity,
            "step": "description_comparison_complete"
        }
    except Exception as e:
        logger.error(f"[LangGraph] Description Comparison failed for order {order_id}: {str(e)}", exc_info=True)
        return {
            **state,
            "description_similarity": None,
            "step": "description_comparison_error"
        }


def should_continue_after_vision(state: ReturnProcessingState) -> Literal["description_comparison", "communication", "end"]:
    """Route after vision node."""
    order_id = state.get("order_id", "unknown")
    
    # Check if image validation failed - go directly to communication agent
    vision_output = state.get("vision_output")
    if vision_output:
        if vision_output.defect_label == "image_mismatch" or "VALIDATION_FAILED" in (vision_output.damage_pattern_analysis or ""):
            logger.info(f"[LangGraph Routing] Image validation failed for order {order_id}, routing directly to Communication Agent")
            return "communication"
    
    if state.get("error"):
        logger.warning(f"[LangGraph Routing] Vision node failed for order {order_id}, routing to END")
        return "end"
    logger.info(f"[LangGraph Routing] Vision node succeeded for order {order_id}, routing to Description Comparison")
    return "description_comparison"


def should_continue_after_description_comparison(state: ReturnProcessingState) -> Literal["policy", "end"]:
    """Route after description comparison node."""
    order_id = state.get("order_id", "unknown")
    if state.get("error"):
        logger.warning(f"[LangGraph Routing] Description comparison failed for order {order_id}, routing to END")
        return "end"
    
    # Always continue to policy check - description similarity is just one factor
    logger.info(f"[LangGraph Routing] Description comparison complete for order {order_id}, routing to PolicyAgent")
    return "policy"


def should_continue_after_policy(state: ReturnProcessingState) -> Literal["resolution", "end"]:
    """Route after policy node."""
    order_id = state.get("order_id", "unknown")
    if state.get("error"):
        logger.warning(f"[LangGraph Routing] Policy node failed for order {order_id}, routing to END")
        return "end"
    logger.info(f"[LangGraph Routing] Policy node succeeded for order {order_id}, routing to ResolutionAgent")
    return "resolution"


def should_continue_after_resolution(state: ReturnProcessingState) -> Literal["communication", "end"]:
    """Route after resolution node with conditional logic."""
    order_id = state.get("order_id", "unknown")
    if state.get("error"):
        logger.warning(f"[LangGraph Routing] Resolution node failed for order {order_id}, routing to END")
        return "end"
    
    # Always route to communication agent to generate user message
    decision = state.get("ai_decision")
    logger.info(f"[LangGraph Routing] Resolution node succeeded for order {order_id}, decision: {decision}, routing to CommunicationAgent")
    return "communication"


def create_returns_workflow() -> StateGraph:
    """Create and configure the return processing workflow."""
    workflow = StateGraph(ReturnProcessingState)
    
    # Add nodes
    workflow.add_node("vision", vision_node)
    workflow.add_node("description_comparison", description_comparison_node)
    workflow.add_node("policy", policy_node)
    workflow.add_node("resolution", resolution_node)
    workflow.add_node("communication", communication_node)
    
    # Set entry point
    workflow.set_entry_point("vision")
    
    # Add edges with conditional routing
    workflow.add_conditional_edges(
        "vision",
        should_continue_after_vision,
        {
            "description_comparison": "description_comparison",
            "communication": "communication",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "description_comparison",
        should_continue_after_description_comparison,
        {
            "policy": "policy",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "policy",
        should_continue_after_policy,
        {
            "resolution": "resolution",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "resolution",
        should_continue_after_resolution,
        {
            "communication": "communication",
            "end": END
        }
    )
    
    workflow.add_edge("communication", END)
    
    return workflow.compile()


# Global workflow instance
returns_workflow = create_returns_workflow()

