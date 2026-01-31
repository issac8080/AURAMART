"""
Return & Exchange Models (Authentication Removed)
Adapted from old return system for autonomous operation
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DamageType(str, Enum):
    """Types of damage for return requests"""
    PHYSICAL = "PHYSICAL"
    FUNCTIONAL = "FUNCTIONAL"
    COSMETIC = "COSMETIC"
    PACKAGING = "PACKAGING"
    MISSING_PARTS = "MISSING_PARTS"
    WRONG_ITEM = "WRONG_ITEM"
    SIZE_ISSUE = "SIZE_ISSUE"
    COLOR_ISSUE = "COLOR_ISSUE"
    QUALITY_ISSUE = "QUALITY_ISSUE"
    OTHER = "OTHER"


class ReturnStatus(str, Enum):
    """Return request statuses"""
    PENDING = "PENDING"
    MANUAL_REVIEW_PENDING = "MANUAL_REVIEW_PENDING"
    AI_APPROVED = "AI_APPROVED"
    AI_REJECTED = "AI_REJECTED"
    ADMIN_APPROVED = "ADMIN_APPROVED"
    ADMIN_REJECTED = "ADMIN_REJECTED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MediaFile(BaseModel):
    """Media file with base64 data and mime type"""
    data: str = Field(..., description="Base64 encoded image/video data")
    mime_type: str = Field(..., description="MIME type (e.g., image/jpeg, image/png, video/mp4)")
    filename: Optional[str] = Field(None, description="Original filename")


class ReturnRequest(BaseModel):
    """
    Return request model (Authentication Removed)
    Works autonomously with Order ID and Product ID
    """
    order_id: str = Field(..., description="Order ID from AuraShop")
    product_id: Optional[str] = Field(None, description="Product ID/SKU")
    product_name: Optional[str] = Field(None, description="Product name")
    product_category: str = Field(..., description="Product category")
    
    # Customer contact info (replaces authentication)
    customer_email: Optional[str] = Field(None, description="Customer email for updates")
    customer_phone: Optional[str] = Field(None, description="Customer phone for updates")
    
    # Return details
    damage_type: DamageType = Field(..., description="Type of damage")
    description: str = Field(..., min_length=10, description="Description of the defect")
    
    # Media files for AI analysis
    media_files: Optional[List[str]] = Field(default=[], description="List of media file names/URLs (legacy)")
    media_base64: Optional[List[MediaFile]] = Field(default=[], description="Base64 encoded media files for AI Vision analysis")


class ReturnResponse(BaseModel):
    """Return response with AI/admin decision"""
    id: int
    order_id: str
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    product_category: str
    
    damage_type: str
    description: str
    status: ReturnStatus
    
    # AI decision fields
    ai_decision: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_reason: Optional[str] = None
    probable_cause: Optional[str] = None  # "manufacturing", "user_damage", or "uncertain"
    decision_type: Optional[str] = None
    escalation_reason: Optional[str] = None
    
    # Admin decision fields (for manual reviews)
    admin_decision: Optional[str] = None
    admin_note: Optional[str] = None
    
    # Media
    media_files: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Customer contact
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None

    class Config:
        from_attributes = True


class VisionAgentOutput(BaseModel):
    """Output from Vision AI Agent"""
    defect_label: str
    estimated_severity: str  # "minor", "moderate", "severe"
    damage_type: str
    image_description: Optional[str] = None
    vision_confidence: Optional[float] = None
    probable_cause: Optional[str] = None  # "manufacturing", "user_damage", or "uncertain"
    defect_location: Optional[str] = None
    damage_pattern_analysis: Optional[str] = None


class PolicyAgentOutput(BaseModel):
    """Output from Policy AI Agent"""
    matched_policy_ids: List[str]
    top_policy_texts: List[str]
    raw_cosine_scores: List[float]
    confidence: float
    policy_interpretation: str
    policy_decision: str = "REJECT"  # "APPROVE" or "REJECT"
    policy_applicability: float = 0.0


class ResolutionAgentOutput(BaseModel):
    """Output from Resolution AI Agent"""
    decision: str  # "APPROVED", "REJECTED", "ESCALATE_TO_HUMAN"
    confidence: float
    reason: str
    decision_type: Optional[str] = None
    escalation_reason: Optional[str] = None


class CommunicationAgentOutput(BaseModel):
    """Output from Communication AI Agent"""
    user_message_title: str
    user_message_body: str
