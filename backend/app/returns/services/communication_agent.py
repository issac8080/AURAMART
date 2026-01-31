"""
CommunicationAgent: Generates user-facing messages from AI/admin decisions.
Uses GPT-4o for empathetic, user-friendly message generation when available.
"""
import json
import logging
from typing import Optional
from openai import OpenAI
from app.returns.schemas import CommunicationAgentOutput, ResolutionAgentOutput
from app.returns.config import settings

# Import OPIK tracking if available
try:
    from opik import track
    from opik.integrations.openai import track_openai
    OPIK_AVAILABLE = True
except ImportError:
    OPIK_AVAILABLE = False
    def track(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def track_openai(client):
        return client  # No-op if OPIK not available

logger = logging.getLogger(__name__)


class CommunicationAgent:
    """
    CommunicationAgent generates friendly, user-facing messages.
    
    Converts technical decisions into clear, empathetic communication.
    Uses GPT-4o when available for better message generation.
    """
    
    _client: Optional[OpenAI] = None
    
    @classmethod
    def _get_client(cls) -> Optional[OpenAI]:
        """Get or create OpenAI client with OPIK tracking if API key is available."""
        if cls._client is None:
            api_key = settings.openai_api_key
            if api_key and api_key.strip():
                try:
                    # Create OpenAI client
                    client = OpenAI(api_key=api_key)
                    # Wrap with OPIK tracking for automatic token usage and LLM details
                    if OPIK_AVAILABLE:
                        try:
                            cls._client = track_openai(client)
                            logger.info("[CommunicationAgent] OpenAI client wrapped with OPIK tracking")
                        except Exception as e:
                            logger.warning(f"[CommunicationAgent] Failed to wrap OpenAI client with OPIK: {str(e)}")
                            cls._client = client  # Fallback to unwrapped client
                    else:
                        cls._client = client
                except Exception as e:
                    logger.error(f"Error initializing OpenAI client: {str(e)}")
                    return None
        return cls._client
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if GPT-4o is available (API key is set)."""
        return settings.openai_api_key is not None and settings.openai_api_key.strip() != ""
    
    @staticmethod
    @track(name="communication_agent_generate", type="llm", project_name=settings.opik_project_name if OPIK_AVAILABLE else None, flush=True)
    def generate_message(
        resolution_output: ResolutionAgentOutput = None,
        admin_decision: str = None,
        admin_note: str = None,
        status: str = None,
        product_name: Optional[str] = None,
        product_category: Optional[str] = None,
        user_description: Optional[str] = None
    ) -> CommunicationAgentOutput:
        """
        Generate user-facing message from decision.
        
        Args:
            resolution_output: Output from ResolutionAgent (for AI decisions)
            admin_decision: Admin decision ("APPROVED" or "REJECTED")
            admin_note: Admin's note to user
            status: Current return status
            
        Returns:
            CommunicationAgentOutput with title and body
        """
        if status == "MANUAL_REVIEW_PENDING":
            return CommunicationAgentOutput(
                user_message_title="Under Review",
                user_message_body=(
                    "Your return request has been received and is currently under manual review. "
                    "Our team will examine your case and get back to you soon. "
                    "You will receive an update once the review is complete."
                )
            )
        
        if admin_decision:
            if admin_decision == "APPROVED":
                title = "Return Approved"
                body = (
                    f"Great news! Your return request has been approved. "
                    f"{admin_note if admin_note else 'You can proceed with returning the item.'} "
                    "Please follow the return instructions sent to your email."
                )
            else:  # REJECTED
                title = "Return Request Review"
                body = (
                    f"We've reviewed your return request. "
                    f"{admin_note if admin_note else 'Unfortunately, your request does not meet our return policy criteria at this time.'} "
                    "If you have questions, please contact our support team."
                )
            
            return CommunicationAgentOutput(
                user_message_title=title,
                user_message_body=body
            )
        
        if resolution_output:
            if CommunicationAgent.is_available():
                logger.info(f"[CommunicationAgent] Using GPT-4o for user message generation")
                logger.info(f"[OpenAI API] Model: gpt-4o, Decision: {resolution_output.decision}, Confidence: {resolution_output.confidence:.2%}")
                
                client = CommunicationAgent._get_client()
                if client:
                    try:
                        logger.info(f"[OpenAI API] Sending request to GPT-4o for message generation...")
                        system_prompt = (
                            "You are a professional customer service representative writing a personalized message to a customer "
                            "about their return request decision. CRITICAL: Use ONLY the product name and details provided in the user prompt. "
                            "Do NOT mention incorrect product names, parts, or features that don't match the actual product. "
                            "IMPORTANT: Vary your writing style and tone - don't use the same template every time. "
                            "Your message should be:\n"
                            "- Empathetic and understanding (but vary how you express this)\n"
                            "- Clear and easy to understand\n"
                            "- Professional yet warm (use different phrasings each time)\n"
                            "- Actionable (tell them what to do next if approved, or how to get help if rejected)\n"
                            "- Include specific details from the decision reason, but ONLY reference the correct product and defect described by the customer\n"
                            "- For rejections, explain the specific reason(s) clearly, using the ACTUAL product name and defect from the customer's description\n"
                            "- NEVER mention technical percentages, similarity scores, confidence scores, or other technical metrics\n"
                            "- NEVER mention product parts or features that don't exist for the product (e.g., don't mention 'headband' for a wireless charger)\n"
                            "- Use plain, everyday language that customers can understand\n"
                            "- Vary your sentence structure, opening phrases, and closing statements\n"
                            "- Sometimes start with the decision, sometimes with empathy, sometimes with context\n\n"
                            "Respond ONLY with a JSON object containing 'title' and 'body' fields. "
                            "The title should be concise (max 50 characters) and varied. "
                            "The body should be 3-5 sentences with varied phrasing and structure."
                        )
                        
                        # Build decision-specific guidance
                        decision_guidance = CommunicationAgent._get_decision_guidance(resolution_output.decision)
                        
                        # Build product context
                        product_context = ""
                        if product_name:
                            product_context = f"**Product:** {product_name}"
                            if product_category:
                                product_context += f" (Category: {product_category})"
                            product_context += "\n"
                        
                        description_context = ""
                        if user_description:
                            description_context = f"**Customer's Description:** {user_description}\n"
                        
                        user_prompt = (
                            f"{product_context}"
                            f"{description_context}"
                            f"**Return Decision:** {resolution_output.decision}\n"
                            f"**Detailed Decision Reason:** {resolution_output.reason}\n\n"
                            f"Generate a customer-friendly message explaining this decision. "
                            f"CRITICAL: Use the EXACT product name and details provided above. "
                            f"Do NOT mention incorrect product names or parts (e.g., if the product is a wireless charger, do NOT mention 'headband' or other unrelated items). "
                            f"Match the product mentioned in the customer's description and the product name above. "
                            f"IMPORTANT: Include the specific details from the decision reason above, but explain them in plain language. "
                            f"Do not use vague language - be specific about why the decision was made. "
                            f"DO NOT mention any percentages, scores, or technical metrics - only explain the actual reasons in simple terms. "
                            f"{decision_guidance}"
                        )
                        
                        response = client.chat.completions.create(
                            model="gpt-4o",  # Use gpt-4o explicitly
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            max_tokens=400,
                            temperature=0.8,  # Higher temperature for more variety
                            response_format={"type": "json_object"}  # Request JSON format
                        )
                        
                        logger.info(f"[OpenAI API] GPT-4o API response received - Usage: {response.usage.total_tokens} tokens")
                        
                        message_content = response.choices[0].message.content.strip()
                        message_data = json.loads(message_content)
                        
                        title = message_data.get("title", "Return Request Update")
                        body = message_data.get("body", message_content)
                        
                        # Ensure title is not too long
                        if len(title) > 50:
                            title = title[:47] + "..."
                        
                        logger.info(f"[OpenAI API] User message generated - Title: {title}")
                        logger.info(f"[OpenAI API] Message body preview: {body[:100]}...")
                        
                        return CommunicationAgentOutput(
                            user_message_title=title,
                            user_message_body=body
                        )
                    except Exception as e:
                        logger.warning(f"Error generating GPT-4o message: {str(e)}, falling back to template")
            
            return CommunicationAgent._generate_template_message(resolution_output)
        
        return CommunicationAgentOutput(
            user_message_title="Return Request Received",
            user_message_body="Your return request has been received and is being processed."
        )
    
    @staticmethod
    def _get_decision_guidance(decision: str) -> str:
        """Get GPT-4o guidance text for specific decision types."""
        guidance_map = {
            "APPROVED": (
                "Be positive and congratulatory. Provide clear next steps: "
                "1) Return shipping instructions, 2) Timeline for refund, 3) What to include in the return package."
            ),
            "REJECTED": (
                "Be empathetic and understanding. Explain the specific reason(s) clearly. "
                "Offer support options: 1) How to contact support, 2) What additional information might help, "
                "3) Appeal process if applicable."
            ),
            "ESCALATE_TO_HUMAN": (
                "Be reassuring and professional. Explain that the case needs human review for accuracy. "
                "Provide: 1) Timeline for review (1-2 business days), 2) What will happen next, "
                "3) How they will be notified."
            )
        }
        return guidance_map.get(decision, "Explain the decision clearly and provide next steps.")
    
    @staticmethod
    def _generate_template_message(resolution_output: ResolutionAgentOutput) -> CommunicationAgentOutput:
        """Generate varied template-based messages for all decision types."""
        import random
        decision = resolution_output.decision
        reason = resolution_output.reason
        
        if decision == "APPROVED":
            titles = [
                "Return Approved",
                "Your Return Has Been Approved",
                "Great News - Return Approved",
                "Return Request Approved"
            ]
            bodies = [
                f"Excellent news! We've approved your return request. {reason} You'll receive detailed return shipping instructions via email within 24 hours. Please package the item securely with all original accessories and use the prepaid return label we'll provide. Your refund will be processed within 5-7 business days after we receive and verify the returned item.",
                f"We're happy to let you know that your return has been approved. {reason} Return instructions with a prepaid shipping label will be sent to your email shortly. Make sure to include all original packaging and accessories when returning the item. Once we receive it, we'll process your refund within one week.",
                f"Good news! Your return request is approved. {reason} Check your email for return shipping instructions and a prepaid label within the next 24 hours. Package everything securely, including the original box and all accessories. Refunds typically process in 5-7 business days after we receive the return."
            ]
            title = random.choice(titles)
            body = random.choice(bodies)
            
        elif decision == "REJECTED":
            titles = [
                "Return Request Review",
                "Return Request Decision",
                "About Your Return Request"
            ]
            bodies = [
                f"We've carefully reviewed your return request, but unfortunately we're unable to approve it at this time. {reason} We understand this may be disappointing. If you have additional information, believe there's been an error, or would like to discuss your case further, please reach out to our support team. We're here to help find a solution.",
                f"After reviewing your return request, we cannot approve it based on our current return policy. {reason} We know this isn't the outcome you were hoping for. If you'd like to provide more details or have questions about this decision, our support team is available to assist you. Contact us and we'll do our best to help.",
                f"Thank you for your return request. Unfortunately, we're unable to approve it at this time. {reason} We understand this may be frustrating. If you have more information to share or would like to appeal this decision, please contact our customer support team. We're committed to finding a resolution that works for you."
            ]
            title = random.choice(titles)
            body = random.choice(bodies)
            
        elif decision == "ESCALATE_TO_HUMAN":
            titles = [
                "Under Review",
                "Manual Review Required",
                "Your Return Is Being Reviewed"
            ]
            bodies = [
                f"{reason} To ensure we make the best decision for your situation, your return request requires additional review by our team. We'll carefully examine all the details and get back to you with a decision. You'll receive an email notification once the review is complete, typically within 1-2 business days.",
                f"{reason} Your return request needs a closer look from our review team to ensure we handle it correctly. We're taking the time to carefully evaluate your case. Expect an email update with our decision within 1-2 business days. We appreciate your patience.",
                f"{reason} We want to make sure we get this right, so your return is being reviewed by our team. This allows us to give your case the attention it deserves. We'll send you an email as soon as the review is finished, usually within 1-2 business days. Thank you for your understanding."
            ]
            title = random.choice(titles)
            body = random.choice(bodies)
        else:
            title = "Return Request Update"
            body = f"{reason} If you have questions, please contact our support team."
        
        return CommunicationAgentOutput(
            user_message_title=title,
            user_message_body=body
        )

