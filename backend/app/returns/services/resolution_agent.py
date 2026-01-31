"""
ResolutionAgent: Makes the final decision based on policy interpretation and business rules.
Supports decision types: APPROVED, REJECTED, ESCALATE_TO_HUMAN.
"""
import logging
from datetime import datetime
from typing import Optional
from app.returns.schemas import ResolutionAgentOutput, PolicyAgentOutput, VisionAgentOutput
from app.returns.config import settings

logger = logging.getLogger(__name__)


class ResolutionAgent:
    """
    ResolutionAgent makes the final return decision using structured reasoning.
    
    Decision Types:
    - APPROVED: Return approved automatically
    - REJECTED: Return denied based on policy/rules
    - ESCALATE_TO_HUMAN: Uncertain case, needs human review (same as MANUAL_REVIEW_PENDING status)
    
    The confidence score represents certainty that the specific decision (APPROVED/REJECTED) is correct.
    It is calculated after the decision is made, using a weighted average of multiple factors.
    """
    
    # Return eligibility window (days)
    RETURN_WINDOW_DAYS = 30
    
    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.75
    MEDIUM_CONFIDENCE_THRESHOLD = 0.50
    LOW_CONFIDENCE_THRESHOLD = 0.30
    
    @staticmethod
    def resolve(
        policy_output: PolicyAgentOutput,
        damage_type: str,
        purchase_date: datetime,
        vision_output: Optional[VisionAgentOutput] = None,
        vision_confidence: Optional[float] = None,
        description_similarity: Optional[float] = None
    ) -> ResolutionAgentOutput:
        """
        Resolve return request based on policy interpretation and business rules.
        
        Uses structured reasoning with rule-based logic and LLM-assisted judgment.
        First determines the decision (APPROVED/REJECTED/ESCALATE_TO_HUMAN), then calculates
        confidence specifically for that decision. The confidence represents certainty that
        the decision is correct.
        
        Args:
            policy_output: Output from PolicyAgent (contains policy decision and applicability)
            damage_type: "PHYSICAL" or "FUNCTIONAL"
            purchase_date: Order purchase date
            vision_output: Full VisionAgentOutput (for probable_cause and other details)
            vision_confidence: Confidence from GPT-4o Vision analysis (0.0-1.0)
            description_similarity: Cosine similarity between OpenAI and user descriptions (0.0-1.0)
            
        Returns:
            ResolutionAgentOutput with decision, confidence (certainty in the decision), and reason
        """
        if damage_type == "FUNCTIONAL":
            return ResolutionAgentOutput(
                decision="ESCALATE_TO_HUMAN",
                confidence=0.0,
                reason="Functional damage requires manual review. This should not be processed by AI."
            )
        
        policy_decision = policy_output.policy_decision
        policy_applicability = policy_output.policy_applicability
        policy_confidence = policy_output.confidence
        
        probable_cause = vision_output.probable_cause if vision_output else None
        defect_severity = vision_output.estimated_severity if vision_output else "moderate"
        defect_label = vision_output.defect_label if vision_output else "general_damage"
        
        if vision_output and vision_output.vision_confidence is not None:
            vision_confidence = vision_output.vision_confidence
        
        days_since_purchase = (datetime.utcnow() - purchase_date).days
        within_window = days_since_purchase <= ResolutionAgent.RETURN_WINDOW_DAYS
        
        if damage_type == "WRONG_ITEM" and vision_output and vision_output.defect_label == "wrong_item":
            if within_window:
                logger.info(f"[ResolutionAgent] WRONG_ITEM case - Auto-approving (fulfillment error)")
                return ResolutionAgentOutput(
                    decision="APPROVED",
                    confidence=1.0,
                    reason=f"Return approved. You received the wrong item ({vision_output.defect_location or 'different product'}). This is a fulfillment error on our part, and we apologize for the inconvenience. Please return the item you received, and we will process your refund or send the correct item.",
                    decision_type="APPROVED",
                    escalation_reason=None
                )
            else:
                logger.info(f"[ResolutionAgent] WRONG_ITEM case but outside return window")
        
        threshold = settings.physical_confidence_threshold
        
        logger.info(f"[ResolutionAgent] Decision factors:")
        logger.info(f"  Policy Decision: {policy_decision}")
        logger.info(f"  Policy Applicability: {policy_applicability:.2%}")
        logger.info(f"  Policy Confidence: {policy_confidence:.2%}")
        logger.info(f"  Probable Cause: {probable_cause}")
        logger.info(f"  Defect Severity: {defect_severity}")
        logger.info(f"  Within time window: {within_window} ({days_since_purchase} days)")
        if vision_confidence:
            logger.info(f"  Vision confidence: {vision_confidence:.2%}")
        if description_similarity:
            logger.info(f"  Description similarity: {description_similarity:.2%}")
        
        decision, reason = ResolutionAgent._make_structured_decision(
            policy_decision=policy_decision,
            policy_output=policy_output,
            probable_cause=probable_cause,
            within_window=within_window,
            policy_confidence=policy_confidence,
            threshold=threshold,
            days_since_purchase=days_since_purchase,
            defect_severity=defect_severity,
            defect_label=defect_label
        )
        
        confidence = ResolutionAgent._calculate_decision_confidence(
            decision=decision,
            policy_decision=policy_decision,
            policy_applicability=policy_applicability,
            policy_confidence=policy_confidence,
            within_window=within_window,
            vision_confidence=vision_confidence,
            description_similarity=description_similarity,
            probable_cause=probable_cause
        )
        
        logger.info(f"[ResolutionAgent] Final Decision: {decision} (Confidence: {confidence:.2%})")
        
        escalation_reason = None
        if decision == "ESCALATE_TO_HUMAN":
            escalation_reason = reason
        
        return ResolutionAgentOutput(
            decision=decision,
            confidence=confidence,
            reason=reason,
            decision_type=decision,
            escalation_reason=escalation_reason
        )
    
    @staticmethod
    def _make_structured_decision(
        policy_decision: str,
        policy_output: PolicyAgentOutput,
        probable_cause: Optional[str],
        within_window: bool,
        policy_confidence: float,
        threshold: float,
        days_since_purchase: int,
        defect_severity: str,
        defect_label: str
    ) -> tuple[str, str]:
        """
        Make structured decision using rule-based logic.
        
        Returns:
            Tuple of (decision_type, reason)
        """
        if not within_window:
            days_over = days_since_purchase - ResolutionAgent.RETURN_WINDOW_DAYS
            return (
                "REJECTED",
                ResolutionAgent._generate_rejection_reason(
                    policy_output, days_since_purchase, within_window,
                    policy_decision, policy_confidence, threshold
                )
            )
        
        if probable_cause == "user_damage" and policy_decision == "REJECT":
            return (
                "REJECTED",
                ResolutionAgent._generate_rejection_reason(
                    policy_output, days_since_purchase, within_window,
                    policy_decision, policy_confidence, threshold
                )
            )
        
        if policy_decision == "REJECT":
            return (
                "REJECTED",
                ResolutionAgent._generate_rejection_reason(
                    policy_output, days_since_purchase, within_window,
                    policy_decision, policy_confidence, threshold
                )
            )
        
        if policy_decision == "APPROVE" and policy_confidence >= threshold:
            return (
                "APPROVED",
                ResolutionAgent._generate_approval_reason(policy_output, days_since_purchase)
            )
        
        if (probable_cause == "manufacturing" and 
            policy_decision == "APPROVE" and 
            policy_confidence >= (threshold - 0.1)):
            return (
                "APPROVED",
                ResolutionAgent._generate_approval_reason(policy_output, days_since_purchase)
            )
        
        if policy_confidence < ResolutionAgent.LOW_CONFIDENCE_THRESHOLD:
            return (
                "ESCALATE_TO_HUMAN",
                ResolutionAgent._generate_escalation_reason(
                    policy_output, probable_cause, policy_confidence, defect_severity
                )
            )
        
        if probable_cause == "uncertain" and policy_confidence < threshold:
            return (
                "ESCALATE_TO_HUMAN",
                ResolutionAgent._generate_escalation_reason(
                    policy_output, probable_cause, policy_confidence, defect_severity
                )
            )
        
        return (
            "ESCALATE_TO_HUMAN",
            ResolutionAgent._generate_escalation_reason(
                policy_output, probable_cause, policy_confidence, defect_severity
            )
        )
    
    @staticmethod
    def _calculate_decision_confidence(
        decision: str,
        policy_decision: str,
        policy_applicability: float,
        policy_confidence: float,
        within_window: bool,
        vision_confidence: Optional[float],
        description_similarity: Optional[float],
        probable_cause: Optional[str] = None
    ) -> float:
        """
        Calculate confidence that the specific decision (APPROVED/REJECTED) is correct.
        
        This represents the system's certainty that it should approve or reject the return.
        The confidence is calculated differently based on the decision:
        - For APPROVED: Confidence that approval is correct
        - For REJECTED: Confidence that rejection is correct
        - For ESCALATE_TO_HUMAN: Low confidence (uncertainty)
        
        Confidence factors (weighted average):
        1. Policy confidence (40% weight) - from PolicyAgent interpretation
        2. Time window compliance (20% weight)
        3. Description match (20% weight, if available)
        4. Vision confidence (20% weight, if available)
        5. Probable cause alignment (10% weight, if available)
        
        Args:
            decision: The decision made ("APPROVED", "REJECTED", or "ESCALATE_TO_HUMAN")
            policy_decision: "APPROVE" or "REJECT"
            policy_applicability: How well policy applies (0.0-1.0)
            policy_confidence: Confidence from PolicyAgent
            within_window: Whether within return window
            vision_confidence: Vision analysis confidence
            description_similarity: Description match score
            probable_cause: Probable cause from vision analysis
            
        Returns:
            Confidence in the decision (0.0-1.0)
        """
        if decision == "ESCALATE_TO_HUMAN":
            return max(0.0, min(0.3, policy_confidence * 0.5))
        
        factors = []
        weights = []
        
        if decision == "APPROVED" and policy_decision == "APPROVE":
            boosted_policy_confidence = min(1.0, policy_confidence + 0.15)
            factors.append(boosted_policy_confidence)
            logger.info(f"[ResolutionAgent] Confidence for {decision} - Policy: {policy_confidence:.2%} (boosted to {boosted_policy_confidence:.2%}, weight: 40%)")
        else:
            factors.append(policy_confidence)
            logger.info(f"[ResolutionAgent] Confidence for {decision} - Policy: {policy_confidence:.2%} (weight: 40%)")
        weights.append(0.4)
        
        if decision == "APPROVED":
            time_factor = 1.0 if within_window else 0.0
        else:
            time_factor = 0.8 if within_window else 1.0
        factors.append(time_factor)
        weights.append(0.2)
        logger.info(f"[ResolutionAgent] Confidence for {decision} - Time window: {time_factor:.2%} (weight: 20%)")
        
        if description_similarity is not None:
            desc_factor = description_similarity if description_similarity >= 0.5 else 0.0
            factors.append(desc_factor)
            weights.append(0.2)
            logger.info(f"[ResolutionAgent] Confidence for {decision} - Description match: {desc_factor:.2%} (weight: 20%)")
        else:
            weights[0] += 0.1
            weights[1] += 0.1
        
        if vision_confidence is not None:
            factors.append(vision_confidence)
            weights.append(0.2)
            logger.info(f"[ResolutionAgent] Confidence for {decision} - Vision: {vision_confidence:.2%} (weight: 20%)")
        else:
            weights[0] += 0.1
            weights[1] += 0.1
        
        if probable_cause:
            if decision == "APPROVED":
                if probable_cause == "manufacturing" and policy_decision == "APPROVE":
                    cause_factor = 1.0
                elif probable_cause == "uncertain":
                    cause_factor = 0.6
                else:
                    cause_factor = 0.7
            else:
                if probable_cause == "user_damage" and policy_decision == "REJECT":
                    cause_factor = 1.0
                elif probable_cause == "uncertain":
                    cause_factor = 0.5
                else:
                    cause_factor = 0.7
            
            factors.append(cause_factor)
            weights.append(0.1)
            logger.info(f"[ResolutionAgent] Confidence for {decision} - Probable cause alignment: {cause_factor:.2%} (weight: 10%)")
        else:
            if len(weights) > 0:
                weights[0] += 0.05
            if len(weights) > 1:
                weights[1] += 0.05
        
        total_weight = sum(weights)
        if total_weight > 0:
            confidence = sum(f * w for f, w in zip(factors, weights)) / total_weight
        else:
            confidence = 0.0
        
        confidence = max(0.0, min(1.0, confidence))
        
        logger.info(f"[ResolutionAgent] Final confidence for {decision}: {confidence:.2%}")
        
        return confidence
    
    @staticmethod
    def _generate_approval_reason(
        policy_output: PolicyAgentOutput,
        days_since_purchase: int
    ) -> str:
        """Generate approval reason text."""
        interpretation = policy_output.policy_interpretation
        
        reason = (
            f"Return approved. Your request was submitted {days_since_purchase} days after purchase, "
            f"which is within our {ResolutionAgent.RETURN_WINDOW_DAYS}-day return window. "
            f"\n\n{interpretation}"
        )
        
        return reason
    
    @staticmethod
    def _generate_rejection_reason(
        policy_output: PolicyAgentOutput,
        days_since_purchase: int,
        within_window: bool,
        policy_decision: str,
        policy_confidence: float,
        threshold: float
    ) -> str:
        """Generate detailed rejection reason text."""
        reasons = []
        
        if policy_decision == "REJECT":
            reasons.append("the return policy does not cover this type of damage")
        
        if not within_window:
            days_over = days_since_purchase - ResolutionAgent.RETURN_WINDOW_DAYS
            reasons.append(
                f"the return window has expired (request submitted {days_since_purchase} days after purchase, "
                f"which exceeds our {ResolutionAgent.RETURN_WINDOW_DAYS}-day return window by {days_over} day(s))"
            )
        
        if policy_confidence < threshold:
            if policy_decision == "APPROVE":
                reasons.append(
                    "there is insufficient confidence in the assessment to automatically approve this return"
                )
        
        if not reasons:
            reason_text = "Return rejected. The request does not meet our automatic approval criteria. "
        else:
            reason_text = f"Return rejected because {' and '.join(reasons)}. "
        
        interpretation = policy_output.policy_interpretation
        reason_text += f"\n\n{interpretation}"
        
        if not within_window:
            reason_text += "\n\nIf you believe there are extenuating circumstances, please contact our support team for manual review."
        elif policy_decision == "REJECT":
            reason_text += "\n\nIf you have additional information or believe this decision is incorrect, please contact our support team."
        else:
            reason_text += "\n\nIf you have questions, please contact our support team for assistance."
        
        return reason_text
    
    @staticmethod
    def _generate_escalation_reason(
        policy_output: PolicyAgentOutput,
        probable_cause: Optional[str],
        policy_confidence: float,
        defect_severity: str
    ) -> str:
        """Generate escalation reason text."""
        reasons = []
        
        if probable_cause == "uncertain":
            reasons.append("the cause of the damage could not be determined with sufficient certainty")
        
        if policy_confidence < ResolutionAgent.LOW_CONFIDENCE_THRESHOLD:
            reasons.append("there is insufficient confidence in the assessment")
        
        if defect_severity == "severe":
            reasons.append("the severity of the defect requires human review")
        
        reason_text = "This return request requires manual review by our support team. "
        if reasons:
            reason_text += f"Reason: {', '.join(reasons)}. "
        
        reason_text += "\n\nOur team will examine your case and get back to you within 1-2 business days. "
        reason_text += "You will receive an email notification once the review is complete."
        
        return reason_text
    

