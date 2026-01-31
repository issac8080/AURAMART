"""
VisionAgent: Uses GPT-4o Vision API to analyze images/videos and extract defect information.
"""
import json
import base64
import os
import logging
from typing import List, Optional, Dict
from openai import OpenAI
from app.returns.schemas import VisionAgentOutput
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


class VisionAgent:
    """
    VisionAgent uses GPT-4o Vision to analyze uploaded media files.
    
    For images: Direct analysis with GPT-4o Vision
    For videos: Extracts key frames or uses description (GPT-4o Vision can analyze video frames)
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
                    logger.info("[VisionAgent] OpenAI client wrapped with OPIK tracking")
                except Exception as e:
                    logger.warning(f"[VisionAgent] Failed to wrap OpenAI client with OPIK: {str(e)}")
                    cls._client = client  # Fallback to unwrapped client
            else:
                cls._client = client
        return cls._client
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if GPT-4o Vision is available (API key is set)."""
        return settings.openai_api_key is not None and settings.openai_api_key.strip() != ""
    
    @staticmethod
    @track(name="vision_agent_analyze", type="llm", project_name=settings.opik_project_name if OPIK_AVAILABLE else None, flush=True)
    def analyze_defect(
        description: str,
        damage_type: str,
        category: str,
        media_files: Optional[List[str]] = None,
        media_base64: Optional[List[Dict[str, str]]] = None,
        product_name: Optional[str] = None
    ) -> VisionAgentOutput:
        """
        Analyze defect from description and media using GPT-4o Vision.
        
        Args:
            description: User's description of the defect
            damage_type: "PHYSICAL" or "FUNCTIONAL"
            category: Product category
            media_files: List of media file paths (for local files)
            media_base64: List of dicts with 'data' (base64) and 'mime_type' (for uploaded files)
            
        Returns:
            VisionAgentOutput with defect label and severity
        """
        if not media_files and not media_base64:
            return VisionAgent._analyze_from_description(description, damage_type, category)
        
        try:
            image_contents = []
            
            if media_base64:
                media = media_base64[0]
                if media.get('mime_type', '').startswith('image/'):
                    image_contents.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media['mime_type']};base64,{media['data']}"
                        }
                    })
                    if len(media_base64) > 1:
                        logger.info(f"[VisionAgent] Using first image only (total {len(media_base64)} provided)")
            
            if media_files:
                file_path = media_files[0]
                if os.path.exists(file_path) and file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    with open(file_path, 'rb') as f:
                        image_data = base64.b64encode(f.read()).decode('utf-8')
                        mime_type = "image/jpeg" if file_path.lower().endswith(('.jpg', '.jpeg')) else "image/png"
                        image_contents.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}"
                            }
                        })
                    if len(media_files) > 1:
                        logger.info(f"[VisionAgent] Using first image only (total {len(media_files)} provided)")
            
            if not image_contents:
                # No valid images found, fall back to description
                return VisionAgent._analyze_from_description(description, damage_type, category)
            
            # Call GPT-4o Vision API
            logger.info(f"[VisionAgent] Calling OpenAI GPT-4o Vision API for {len(image_contents)} image(s)")
            logger.info(f"[OpenAI API] Model: gpt-4o, Category: {category}, Damage Type: {damage_type}")
            
            client = VisionAgent._get_client()
            
            system_prompt = (
                "You are an expert product quality inspector analyzing product defects and damage. "
                "Your task is to identify what is in the image and verify it matches what the user is describing. "
                "Be precise, detailed, and objective in your analysis."
            )
            
            product_info = ""
            if product_name:
                product_info = f"Ordered Product Name: {product_name}\n"
            
            user_prompt = (
                f"{product_info}"
                f"Product Category: {category}\n"
                f"Reported Damage Type: {damage_type}\n"
                f"User's Description: {description}\n\n"
                "VALIDATION PRIORITY:\n"
                "The PRIMARY validation is whether the image matches what the user is describing. "
                "The image should show the issue, defect, or situation the user is reporting.\n\n"
                "STEP 1 - DESCRIPTION VALIDATION (PRIMARY - MOST IMPORTANT):\n"
                "Compare what you see in the image to the user's description. "
                "Does the image show what the user is describing?\n"
                "- If user says 'got pants instead of shorts' and image shows pants → image_matches_description = TRUE\n"
                "- If user says 'cracked screen' and image shows a cracked screen → image_matches_description = TRUE\n"
                "- If user says 'cracked screen' but image shows a perfect screen → image_matches_description = FALSE\n"
                "- If user says 'wrong item' and image shows a different product → image_matches_description = TRUE\n"
                "Set 'image_matches_description' to TRUE only if the image clearly shows what the user described.\n\n"
                "STEP 2 - PRODUCT VALIDATION (SECONDARY - INFORMATIONAL):\n"
                "Identify what product/item is actually shown in the image. "
                "Compare it to the ordered product name above (if provided). "
                "Set 'image_matches_product' to TRUE if it matches the ordered product, FALSE otherwise. "
                "Note: For WRONG_ITEM cases, image_matches_product will be FALSE, which is expected and valid.\n\n"
                "STEP 3 - DEFECT ANALYSIS:\n"
                "If image_matches_description is TRUE, proceed to analyze the defect or issue shown in the image.\n\n"
                "Please analyze the provided image carefully and respond with a JSON object containing exactly these fields:\n"
                "- image_matches_description: true or false - PRIMARY VALIDATION. Does the image show what the user is describing? "
                "This is the most important check. If FALSE, the return should be rejected. "
                "If TRUE, proceed with analysis even if the product doesn't match the order.\n"
                "- image_matches_product: true or false - SECONDARY CHECK. Does the image show the ordered product? "
                "This is informational. For WRONG_ITEM cases, this will be FALSE, which is expected.\n"
                "- validation_issue: A clear explanation ONLY if image_matches_description is FALSE. "
                "Explain why the image doesn't match what the user described (e.g., 'User described cracked screen but image shows perfect screen', "
                "'User described receiving wrong item but image shows the correct ordered product'). "
                "Leave empty if image_matches_description is TRUE.\n"
                "- identified_product: What product/item you actually see in the image (be specific, e.g., 'wireless charging pad', 'headphone', 'smartphone', 'pants', 'shorts').\n"
                "- image_description: A clear, natural description of what you see in the image. "
                "If image_matches_description is TRUE, describe the damage, defect, or issue. "
                "If image_matches_description is FALSE, describe what you actually see instead. "
                "Write this as a customer would describe it - use simple, everyday language.\n"
                "- defect_label: A specific defect identifier in snake_case (e.g., 'cracked_screen', 'broken_handle', 'wrong_item', 'scratched_surface'). "
                "If image_matches_description is FALSE, use 'image_mismatch'.\n"
                f"- estimated_severity: One of 'minor', 'moderate', or 'severe'.\n"
                f"- damage_type: '{damage_type}' (must match the reported type)\n"
                "- vision_confidence: A confidence score between 0.0 and 1.0 (as a float) indicating how confident you are in your analysis. "
                "Consider factors like: clarity of the image, visibility of the defect/issue, certainty of your assessment. "
                "0.0 means very uncertain, 1.0 means completely certain.\n"
                "- probable_cause: One of 'manufacturing', 'user_damage', or 'uncertain'. "
                "For WRONG_ITEM, use 'manufacturing' (fulfillment error). "
                "Otherwise, determine the likely origin:\n"
                "  * 'manufacturing': Defects from production or fulfillment errors (e.g., cracks along seams, wrong item sent, material flaws)\n"
                "  * 'user_damage': Damage from misuse (e.g., impact damage, scratches from use, wear patterns)\n"
                "  * 'uncertain': When you cannot determine the cause with reasonable confidence\n"
                "- defect_location: A brief description of where the issue is located or what the issue is "
                "(e.g., 'top right corner of screen', 'handle attachment point', 'received different product').\n"
                "- damage_pattern_analysis: A brief analysis of what you observe. "
                "If image_matches_description is FALSE, explain the mismatch. "
                "Otherwise, explain what patterns or characteristics you observe.\n\n"
                "CRITICAL RULE: Only reject if image_matches_description is FALSE. "
                "If image_matches_description is TRUE, proceed with analysis regardless of image_matches_product value."
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt}
                    ] + image_contents
                }
            ]
            
            logger.info(f"[OpenAI API] Sending request to GPT-4o Vision API...")
            response = client.chat.completions.create(
                model="gpt-4o",  # Use gpt-4o explicitly for vision
                messages=messages,
                max_tokens=500,
                temperature=0.2,  # Lower temperature for more consistent analysis
                response_format={"type": "json_object"}
            )
            
            logger.info(f"[OpenAI API] GPT-4o Vision API response received - Usage: {response.usage.total_tokens} tokens")
            
            # Parse response
            response_text = response.choices[0].message.content
            vision_data = json.loads(response_text)
            
            image_matches_product = vision_data.get("image_matches_product", True)
            image_matches_description = vision_data.get("image_matches_description", True)
            validation_issue = vision_data.get("validation_issue", "")
            identified_product = vision_data.get("identified_product", "")
            
            logger.info(f"[OpenAI API] Validation - Matches description: {image_matches_description}, Matches product: {image_matches_product}")
            if validation_issue:
                logger.warning(f"[OpenAI API] Validation issue: {validation_issue}")
            if identified_product:
                logger.info(f"[OpenAI API] Identified product in image: {identified_product}")
            
            if not image_matches_description:
                error_msg = validation_issue or f"Image shows {identified_product or 'unknown product'}, but expected product is {product_name or 'different product'}"
                logger.error(f"[VisionAgent] Validation failed: {error_msg}")
                
                # Return output with validation failure - workflow will handle rejection
                # Confidence is 1.0 (100%) because we're CERTAIN there's a mismatch
                return VisionAgentOutput(
                    defect_label="image_mismatch",
                    estimated_severity="severe",
                    damage_type=damage_type,
                    image_description=vision_data.get("image_description", f"Image shows: {identified_product}"),
                    vision_confidence=1.0,  # 100% confidence - we're certain there's a mismatch
                    probable_cause="uncertain",
                    defect_location=validation_issue,
                    damage_pattern_analysis=f"VALIDATION_FAILED: {error_msg}"
                )
            
            logger.info(f"[OpenAI API] Parsed GPT-4o Vision response - Defect: {vision_data.get('defect_label')}, Severity: {vision_data.get('estimated_severity')}")
            
            image_description = vision_data.get("image_description", "")
            vision_confidence = float(vision_data.get("vision_confidence", 0.5))
            vision_confidence = max(0.0, min(1.0, vision_confidence))  # Clamp to [0, 1]
            
            logger.info(f"[OpenAI API] Image description generated by GPT-4o Vision:")
            logger.info(f"[OpenAI API] {image_description}")
            logger.info(f"[OpenAI API] Image description length: {len(image_description)} characters")
            logger.info(f"[OpenAI API] Vision confidence: {vision_confidence:.2%}")
            
            probable_cause = vision_data.get("probable_cause", "uncertain")
            if probable_cause not in ["manufacturing", "user_damage", "uncertain"]:
                probable_cause = "uncertain"
            
            logger.info(f"[OpenAI API] Probable cause: {probable_cause}")
            
            return VisionAgentOutput(
                defect_label=vision_data.get("defect_label", "general_damage"),
                estimated_severity=vision_data.get("estimated_severity", "minor"),
                damage_type=damage_type,
                image_description=image_description,
                vision_confidence=vision_confidence,
                probable_cause=probable_cause,
                defect_location=vision_data.get("defect_location"),
                damage_pattern_analysis=vision_data.get("damage_pattern_analysis")
            )
            
        except Exception as e:
            # Log error and fall back to description-based analysis (only for non-validation errors)
            error_msg = str(e)
            logger.error(f"Error in GPT-4o Vision analysis: {error_msg}")
            
            # If it's an API key error, be more explicit
            if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                logger.warning("WARNING: OpenAI API key issue. Please set OPENAI_API_KEY environment variable.")
                logger.warning("Falling back to description-based analysis (limited accuracy)")
            else:
                logger.warning("Falling back to description-based analysis")
            
            return VisionAgent._analyze_from_description(description, damage_type, category)
    
    @staticmethod
    def _analyze_from_description(
        description: str,
        damage_type: str,
        category: str
    ) -> VisionAgentOutput:
        """
        Fallback: Analyze defect from description only (when vision API fails or no images).
        
        This maintains backward compatibility and handles cases where:
        - No images are provided
        - API call fails
        - API key is not configured
        """
        description_lower = description.lower()
        
        # Extract defect label based on keywords
        defect_label = VisionAgent._extract_defect_label(description_lower, category)
        
        # Estimate severity based on keywords
        severity = VisionAgent._estimate_severity(description_lower)
        
        # Estimate probable cause from description
        probable_cause = VisionAgent._estimate_probable_cause(description_lower, category)
        
        return VisionAgentOutput(
            defect_label=defect_label,
            estimated_severity=severity,
            damage_type=damage_type,
            image_description=None,  # No image description in fallback
            vision_confidence=0.3,  # Low confidence for fallback analysis
            probable_cause=probable_cause,
            defect_location=None,
            damage_pattern_analysis=None
        )
    
    @staticmethod
    def _extract_defect_label(description: str, category: str) -> str:
        """Extract a defect label from description."""
        # Simple keyword-based extraction (fallback when vision API unavailable)
        if "crack" in description or "broken" in description:
            if "screen" in description or category == "Electronics":
                return "cracked_screen"
            elif "handle" in description:
                return "broken_handle"
            else:
                return "cracked_item"
        elif "scratch" in description or "scratched" in description:
            return "scratched_surface"
        elif "tear" in description or "ripped" in description:
            return "torn_fabric"
        elif "stain" in description or "stained" in description:
            return "stained_item"
        elif "power" in description or "won't turn on" in description or "not working" in description:
            return "power_failure"
        elif "button" in description and ("not" in description or "broken" in description):
            return "button_malfunction"
        elif "display" in description and ("not" in description or "blank" in description):
            return "display_failure"
        else:
            return "general_damage"
    
    @staticmethod
    def _estimate_severity(description: str) -> str:
        """Estimate severity level from description."""
        # Simple keyword-based severity estimation
        severe_keywords = ["completely", "totally", "unusable", "destroyed", "shattered", "severe"]
        moderate_keywords = ["significant", "noticeable", "major", "considerable"]
        
        description_lower = description.lower()
        
        if any(keyword in description_lower for keyword in severe_keywords):
            return "severe"
        elif any(keyword in description_lower for keyword in moderate_keywords):
            return "moderate"
        else:
            return "minor"
    
    @staticmethod
    def _estimate_probable_cause(description: str, category: str) -> str:
        """Estimate probable cause from description (fallback method)."""
        description_lower = description.lower()
        
        # Manufacturing defect indicators
        manufacturing_keywords = [
            "defect", "flaw", "imperfection", "manufacturing", "factory", "production",
            "seam", "stitching", "uneven", "warped", "misaligned", "missing part",
            "wrong color", "wrong size", "defective", "faulty from", "came broken",
            "arrived damaged", "out of box"
        ]
        
        # User damage indicators
        user_damage_keywords = [
            "dropped", "fell", "accident", "hit", "impact", "scratched from use",
            "worn", "used", "after using", "while using", "my fault", "i dropped",
            "i broke", "i damaged", "spilled", "knocked over"
        ]
        
        manufacturing_count = sum(1 for kw in manufacturing_keywords if kw in description_lower)
        user_damage_count = sum(1 for kw in user_damage_keywords if kw in description_lower)
        
        if manufacturing_count > user_damage_count:
            return "manufacturing"
        elif user_damage_count > manufacturing_count:
            return "user_damage"
        else:
            return "uncertain"
    
    @staticmethod
    def to_json(output: VisionAgentOutput) -> str:
        """Convert VisionAgentOutput to JSON string for storage."""
        return json.dumps(output.model_dump())
