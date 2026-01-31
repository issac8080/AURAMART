"""
PolicyAgent: Uses RAG (Retrieval-Augmented Generation) to match defects with policy clauses.
Uses ChromaDB for vector search and GPT-4o for semantic interpretation.
"""
import json
import logging
from typing import List, Tuple, Optional
from app.chroma_client import get_chroma_client
from app.returns.schemas import PolicyAgentOutput, VisionAgentOutput
from app.returns.config import settings
from openai import OpenAI

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


class PolicyAgent:
    """
    PolicyAgent retrieves relevant policy clauses using semantic search and interprets them.
    
    Uses:
    - ChromaDB for vector search over policy embeddings (retrieval based on similarity)
    - GPT-4o to interpret policies and determine if they support approval or rejection
    - Separates similarity (for retrieval) from confidence (for decision certainty)
    """
    
    _client: Optional[OpenAI] = None
    
    @classmethod
    def _get_client(cls) -> OpenAI:
        """Get or create OpenAI client with OPIK tracking."""
        if cls._client is None:
            api_key = settings.openai_api_key
            if not api_key:
                raise ValueError(
                    "OpenAI API key not found. Please set OPENAI_API_KEY environment variable "
                    "or add it to .env file"
                )
            # Create OpenAI client
            client = OpenAI(api_key=api_key)
            # Wrap with OPIK tracking for automatic token usage and LLM details
            if OPIK_AVAILABLE:
                try:
                    cls._client = track_openai(client)
                    logger.info("[PolicyAgent] OpenAI client wrapped with OPIK tracking")
                except Exception as e:
                    logger.warning(f"[PolicyAgent] Failed to wrap OpenAI client with OPIK: {str(e)}")
                    cls._client = client  # Fallback to unwrapped client
            else:
                cls._client = client
        return cls._client
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if GPT-4o is available (API key is set)."""
        return settings.openai_api_key is not None and settings.openai_api_key.strip() != ""
    
    @staticmethod
    def match_policy(
        description: str,
        vision_output: VisionAgentOutput,
        product_category: str,
        n_results: int = 10
    ) -> PolicyAgentOutput:
        """
        Match defect description with relevant policy clauses and interpret them.
        
        Enhanced to retrieve and synthesize multiple policies for comprehensive analysis.
        
        Args:
            description: User's defect description
            vision_output: Output from VisionAgent
            product_category: Product category
            n_results: Number of policy clauses to retrieve (default: 10)
            
        Returns:
            PolicyAgentOutput with matched policies, interpretation, and decision confidence
        """
        query_text = (
            f"{description} {vision_output.defect_label} {vision_output.estimated_severity} "
            f"{vision_output.probable_cause or ''} {product_category}"
        )
        
        chroma_client = get_chroma_client()
        
        policy_matches = chroma_client.get_cosine_similarity_scores(
            query_text=query_text,
            product_category=product_category,
            n_results=n_results
        )
        
        policy_details = chroma_client.query_policies(
            query_text=query_text,
            product_category=product_category,
            n_results=n_results
        )
        
        matched_policy_ids = [match[0] for match in policy_matches]
        cosine_scores = [match[1] for match in policy_matches]
        policy_texts = [detail["text"] for detail in policy_details]
        policy_titles = [detail.get("title", "Policy") for detail in policy_details]
        
        logger.info(f"[PolicyAgent] Found {len(policy_matches)} policy matches for category '{product_category}'")
        logger.info(f"[PolicyAgent] Cosine similarity scores (for retrieval): {[f'{s:.2%}' for s in cosine_scores[:5]]}")
        
        if not policy_texts:
            logger.warning(f"[PolicyAgent] No policies found for category '{product_category}'")
            return PolicyAgentOutput(
                matched_policy_ids=[],
                top_policy_texts=[],
                raw_cosine_scores=[],
                confidence=0.0,
                policy_interpretation="No relevant policies found for this product category and damage type.",
                policy_decision="REJECT",
                policy_applicability=0.0
            )
        
        # Use GPT-4o to synthesize multiple policies and determine decision
        max_similarity = cosine_scores[0] if cosine_scores else 0.0
        
        interpretation, policy_decision, applicability = PolicyAgent._interpret_policies_with_gpt4o(
            policy_texts=policy_texts,
            policy_titles=policy_titles,
            policy_ids=matched_policy_ids[:5],  # Use top 5 for synthesis
            description=description,
            vision_output=vision_output,
            product_category=product_category
        )
        
        # Calculate confidence based on policy interpretation, NOT just similarity
        # Confidence = how certain we are about the decision
        confidence = PolicyAgent._calculate_decision_confidence(
            policy_decision=policy_decision,
            applicability=applicability,
            similarity=max_similarity
        )
        
        logger.info(f"[PolicyAgent] Policy Decision: {policy_decision}, Applicability: {applicability:.2%}, Confidence: {confidence:.2%}")
        
        return PolicyAgentOutput(
            matched_policy_ids=matched_policy_ids,
            top_policy_texts=policy_texts,
            raw_cosine_scores=cosine_scores,
            confidence=confidence,
            policy_interpretation=interpretation,
            policy_decision=policy_decision,
            policy_applicability=applicability
        )
    
    @staticmethod
    @track(name="policy_agent_interpret", type="llm", project_name=settings.opik_project_name if OPIK_AVAILABLE else None, flush=True)
    def _interpret_policies_with_gpt4o(
        policy_texts: List[str],
        policy_titles: List[str],
        policy_ids: List[str],
        description: str,
        vision_output: VisionAgentOutput,
        product_category: str
    ) -> Tuple[str, str, float]:
        """
        Use GPT-4o to synthesize multiple policies and determine if they support approval or rejection.
        
        Answers specific questions:
        - Is cracked screen covered?
        - Is user-caused damage allowed?
        - Is return window expired?
        - Is product category eligible for exchange?
        
        Returns:
            Tuple of (interpretation, decision, applicability)
            - interpretation: Human-readable explanation with policy citations
            - decision: "APPROVE" or "REJECT"
            - applicability: 0.0-1.0 score of how well the policies apply
        """
        # Fallback if GPT-4o not available
        if not PolicyAgent.is_available():
            logger.warning("[PolicyAgent] GPT-4o not available, using fallback interpretation")
            return PolicyAgent._fallback_interpretation(policy_texts[0] if policy_texts else "", vision_output)
        
        try:
            client = PolicyAgent._get_client()
            
            # Build policy context with citations
            policies_context = "\n\n".join([
                f"Policy {i+1} (ID: {policy_ids[i] if i < len(policy_ids) else 'N/A'}, Title: {policy_titles[i] if i < len(policy_titles) else 'N/A'}):\n{text}"
                for i, text in enumerate(policy_texts[:5])  # Use top 5 for synthesis
            ])
            
            # Calculate days since purchase (if available in context, otherwise estimate)
            probable_cause = vision_output.probable_cause or "uncertain"
            
            prompt = f"""You are an expert return policy analyst. Analyze multiple return policies to determine if they support or reject a return request.

Product Category: {product_category}
User's Description: {description}
Detected Defect: {vision_output.defect_label.replace('_', ' ')}
Severity: {vision_output.estimated_severity}
Probable Cause: {probable_cause}

IMPORTANT: When analyzing the policies and generating your reasoning, refer to the ACTUAL product category and the specific defect described by the user. 
Do not confuse the product with other items or mention incorrect product parts. Match your analysis to the user's description.

Relevant Policies:
{policies_context}

Answer these specific questions:
1. Is this type of defect (e.g., cracked screen, broken handle) covered by the policies?
2. Is {probable_cause} damage allowed or excluded?
3. What is the return time window, and is this request within it?
4. Is this product category eligible for return/exchange?
5. Are there any special conditions or exceptions that apply?

Synthesize the policies to provide a comprehensive answer. If policies conflict, prioritize the most specific or restrictive policy.

Respond ONLY with a JSON object in this exact format:
{{
    "decision": "APPROVE or REJECT",
    "applicability": 0.0 to 1.0,
    "reasoning": "Detailed explanation citing specific policies. Include policy IDs when referencing them. Explain why the decision was made based on the policies.",
    "answers": {{
        "defect_covered": "yes/no/uncertain - with brief explanation",
        "damage_type_allowed": "yes/no/uncertain - with brief explanation",
        "time_window_compliant": "yes/no/uncertain - with brief explanation",
        "category_eligible": "yes/no/uncertain - with brief explanation"
    }}
}}

Be precise: If policies say damage is NOT covered, the decision is REJECT. If policies say it IS covered, the decision is APPROVE."""

            logger.info("[PolicyAgent] Calling GPT-4o for multi-policy synthesis and interpretation")
            
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a policy interpretation expert. Analyze and synthesize multiple return policies to determine if they support or reject return requests. Provide detailed reasoning with policy citations."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,  # Increased for detailed synthesis
                temperature=0.2,  # Low temperature for consistent interpretation
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            decision = result.get("decision", "REJECT").upper()
            if decision not in ["APPROVE", "REJECT"]:
                decision = "REJECT"
            
            applicability = float(result.get("applicability", 0.5))
            applicability = max(0.0, min(1.0, applicability))
            
            # Build comprehensive reasoning with answers
            reasoning = result.get("reasoning", "Policy interpretation completed.")
            answers = result.get("answers", {})
            
            # Enhance reasoning with specific answers
            if answers:
                reasoning += "\n\nSpecific Policy Answers:\n"
                for question, answer in answers.items():
                    reasoning += f"- {question.replace('_', ' ').title()}: {answer}\n"
            
            logger.info(f"[PolicyAgent] GPT-4o multi-policy interpretation - Decision: {decision}, Applicability: {applicability:.2%}")
            
            return reasoning, decision, applicability
            
        except Exception as e:
            logger.error(f"[PolicyAgent] Error in GPT-4o policy interpretation: {str(e)}")
            return PolicyAgent._fallback_interpretation(policy_texts[0] if policy_texts else "", vision_output)
    
    @staticmethod
    def _fallback_interpretation(
        policy_text: str,
        vision_output: VisionAgentOutput
    ) -> Tuple[str, str, float]:
        """
        Fallback interpretation when GPT-4o is not available.
        Uses keyword-based heuristics.
        """
        policy_lower = policy_text.lower()
        
        # Check for rejection keywords
        reject_keywords = ["not covered", "not eligible", "excluded", "not returnable", "no refund", "cannot be returned"]
        approve_keywords = ["covered", "eligible", "returnable", "refund", "return accepted"]
        
        reject_count = sum(1 for kw in reject_keywords if kw in policy_lower)
        approve_count = sum(1 for kw in approve_keywords if kw in policy_lower)
        
        if reject_count > approve_count:
            decision = "REJECT"
            applicability = 0.6
        elif approve_count > reject_count:
            decision = "APPROVE"
            applicability = 0.6
        else:
            decision = "REJECT"  # Conservative default
            applicability = 0.3
        
        severity_text = vision_output.estimated_severity
        defect_text = vision_output.defect_label.replace("_", " ")
        
        interpretation = (
            f"Based on the {severity_text} {defect_text} reported, "
            f"the policy states: '{policy_text[:150]}...' "
            f"This appears to {decision.lower()} the return request."
        )
        
        logger.info(f"[PolicyAgent] Fallback interpretation - Decision: {decision}, Applicability: {applicability:.2%}")
        
        return interpretation, decision, applicability
    
    @staticmethod
    def _calculate_decision_confidence(
        policy_decision: str,
        applicability: float,
        similarity: float
    ) -> float:
        """
        Calculate confidence in the decision based on multiple factors.
        
        This is NOT the same as similarity! Confidence measures how certain we are
        about the decision, considering:
        - How applicable the policy is to this case
        - How clearly the policy supports the decision
        - How relevant the retrieved policy is (similarity)
        
        Args:
            policy_decision: "APPROVE" or "REJECT"
            applicability: How well the policy applies (0.0-1.0)
            similarity: Cosine similarity used for retrieval (0.0-1.0)
            
        Returns:
            Confidence score (0.0-1.0)
        """
        # Confidence is based on:
        # 1. Policy applicability (70% weight) - how well it applies to this case
        # 2. Similarity (30% weight) - how relevant the retrieved policy is
        
        confidence = (applicability * 0.7) + (similarity * 0.3)
        confidence = max(0.0, min(1.0, confidence))
        
        logger.info(f"[PolicyAgent] Confidence calculation: applicability={applicability:.2%} (70%) + similarity={similarity:.2%} (30%) = {confidence:.2%}")
        
        return confidence
    
    @staticmethod
    def to_json(output: PolicyAgentOutput) -> str:
        """Convert PolicyAgentOutput to JSON string for storage."""
        return json.dumps(output.model_dump())
