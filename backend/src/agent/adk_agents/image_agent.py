"""
ADK Image Agent - Analyzes images using ADK LlmAgent with multimodal support.

Converts the original ImageAgent to use ADK LlmAgent with Gemini's multimodal capabilities.
"""

import os
from typing import Dict, Any, List
from pathlib import Path

try:
    from google.adk.agents import LlmAgent
    from google.genai import types
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    LlmAgent = None


class ADKImageAgent:
    """ADK-based agent for image analysis with multimodal support."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = os.getenv("AGENT_MODEL", "gemini-2.0-flash")
        self.agent = None
        
        if not ADK_AVAILABLE:
            print("⚠️  ADK not available, ImageAgent will use fallback")
            return
        
        if not self.api_key:
            print("⚠️  Warning: GOOGLE_AI_API_KEY or GOOGLE_API_KEY not set")
            return
        
        # Ensure GOOGLE_API_KEY is set for ADK (ADK uses GOOGLE_API_KEY internally)
        if not os.getenv("GOOGLE_API_KEY") and self.api_key:
            os.environ["GOOGLE_API_KEY"] = self.api_key
        
        try:
            # Import ADK tools
            from ..adk_tools import get_adk_tools
            
            # Create ADK LlmAgent with multimodal support
            # ADK reads GOOGLE_API_KEY from environment automatically
            self.agent = LlmAgent(
                model=self.model_name,
                name="image_agent",
                description="Specialized agent for analyzing insurance claim images (damage photos, scene photos)",
                instruction="""You are an insurance claim image analysis agent.

Your job is to analyze insurance claim images and assess damage.

**Process:**
1. First, if you need to verify the image, call verify_image(claim_id, image_path) tool
   - This tool costs $0.15 USDC and handles payment automatically via x402
   - The tool will analyze the image and provide damage assessment
2. Analyze the provided image(s) for damage using multimodal capabilities
3. Identify: damage type, affected parts/areas, severity
4. Estimate repair/replacement cost if possible
5. Check image authenticity (signs of tampering, staging, etc.)
6. Return structured JSON with your findings

**Important:**
- You have access to verify_image tool - use it when you need to verify image authenticity
- The tool handles payment automatically, you don't need to worry about payment processing
- Combine tool results with your own analysis for best results

**Output Format:**
Return a JSON object with:
- damage_type: string (collision, fire, water, theft, etc.)
- affected_parts: array of strings
- severity: string (minor, moderate, severe, total)
- estimated_cost: number or null
- confidence: float (0.0-1.0)
- valid: boolean (true if image appears authentic)
- notes: string (any observations)

Be thorough and accurate in your damage assessment.""",
                tools=get_adk_tools(),  # Include all ADK tools
            )
        except Exception as e:
            print(f"Failed to initialize ADK ImageAgent: {e}")
            self.agent = None
    
    async def analyze(
        self,
        claim_id: str,
        images: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze images for a claim using ADK agent.
        
        Args:
            claim_id: Claim identifier
            images: List of image evidence with file_path
            
        Returns:
            {
                "summary": str,
                "damage_assessment": dict,
                "valid": bool,
                "confidence": float,
                "analysis_id": str
            }
        """
        if not images:
            return {
                "summary": "No images provided",
                "damage_assessment": {},
                "valid": False,
                "confidence": 0.0,
                "analysis_id": None
            }
        
        if not self.agent:
            # Fallback to mock analysis
            return self._mock_analysis(claim_id, images)
        
        # Analyze each image with ADK agent
        results = []
        for img in images:
            file_path = img.get("file_path")
            if not file_path or not Path(file_path).exists():
                continue
            
            try:
                result = await self._analyze_image_with_adk(file_path, claim_id)
                results.append(result)
            except Exception as e:
                print(f"Error analyzing image {file_path}: {e}")
                results.append({
                    "valid": False,
                    "error": str(e),
                    "confidence": 0.0
                })
        
        if not results:
            return {
                "summary": "No valid images could be analyzed",
                "damage_assessment": {},
                "valid": False,
                "confidence": 0.0,
                "analysis_id": None
            }
        
        # Aggregate results
        valid_count = sum(1 for r in results if r.get("valid", False))
        avg_confidence = sum(r.get("confidence", 0.0) for r in results) / len(results)
        
        # Aggregate damage assessment
        damage_assessment = self._aggregate_damage_assessments(results)
        
        return {
            "summary": f"Analyzed {len(results)} image(s). {valid_count} valid.",
            "damage_assessment": damage_assessment,
            "valid": valid_count > 0,
            "confidence": avg_confidence,
            "analysis_id": f"img_{claim_id}",
            "individual_results": results
        }
    
    async def _analyze_image_with_adk(
        self,
        file_path: str,
        claim_id: str
    ) -> Dict[str, Any]:
        """Analyze a single image using ADK agent with multimodal support."""
        try:
            # Read file
            file_data = Path(file_path).read_bytes()
            file_name = Path(file_path).name
            
            # Determine MIME type
            mime_type = "image/jpeg"
            if file_name.endswith(".png"):
                mime_type = "image/png"
            elif file_name.endswith(".webp"):
                mime_type = "image/webp"
            
            # Create multimodal content for ADK agent
            prompt = f"""Analyze this insurance claim image (Claim ID: {claim_id}) and assess:
1. Damage type (collision, fire, water, theft, etc.)
2. Affected parts/areas
3. Severity (minor, moderate, severe, total)
4. Estimated repair/replacement cost
5. Image authenticity (signs of tampering, staging, etc.)

Return a JSON object with:
- damage_type: string
- affected_parts: array of strings
- severity: string (minor, moderate, severe, total)
- estimated_cost: number or null
- confidence: float (0.0-1.0)
- valid: boolean (true if image appears authentic)
- notes: string (any observations)"""
            
            # Create content parts with multimodal support
            content_parts = [
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=file_data, mime_type=mime_type)
            ]
            
            # Run ADK agent with multimodal input
            from ..adk_runtime import get_adk_runtime
            
            runtime = get_adk_runtime()
            runner = runtime.create_runner(
                app_name="claimledger",
                agent=self.agent
            )
            
            # Ensure session exists before using it
            user_id = f"claim_{claim_id}"
            session_id = f"img_analysis_{claim_id}"
            await runtime.get_or_create_session(user_id, session_id)
            
            # Create user message with multimodal content
            user_message = types.Content(
                role="user",
                parts=content_parts
            )
            
            # Run agent and collect response
            response_text = ""
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=user_message
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            response_text += part.text
                if event.is_final_response():
                    break
            
            # Parse response
            import json
            import re
            
            # Try to extract JSON from response
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    assessment = json.loads(json_match.group())
                except:
                    assessment = self._parse_text_response(response_text)
            else:
                assessment = self._parse_text_response(response_text)
            
            return {
                "valid": assessment.get("valid", True),
                "damage_assessment": assessment,
                "confidence": assessment.get("confidence", 0.8),
                "notes": assessment.get("notes", "")
            }
            
        except Exception as e:
            print(f"Error in ADK image analysis: {e}")
            return {
                "valid": False,
                "error": str(e),
                "confidence": 0.0
            }
    
    def _parse_text_response(self, text: str) -> Dict[str, Any]:
        """Parse text response when JSON extraction fails."""
        damage_type = "unknown"
        if "collision" in text.lower() or "crash" in text.lower():
            damage_type = "collision"
        elif "fire" in text.lower():
            damage_type = "fire"
        elif "water" in text.lower() or "flood" in text.lower():
            damage_type = "water"
        
        return {
            "damage_type": damage_type,
            "affected_parts": ["vehicle"],
            "severity": "moderate",
            "estimated_cost": None,
            "confidence": 0.7,
            "valid": True,
            "notes": text
        }
    
    def _aggregate_damage_assessments(
        self,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate damage assessments from multiple images."""
        if not results:
            return {}
        
        damage_types = []
        affected_parts = set()
        severities = []
        costs = []
        confidences = []
        
        for result in results:
            assessment = result.get("damage_assessment", {})
            if assessment:
                if "damage_type" in assessment:
                    damage_types.append(assessment["damage_type"])
                if "affected_parts" in assessment:
                    affected_parts.update(assessment["affected_parts"])
                if "severity" in assessment:
                    severities.append(assessment["severity"])
                if "estimated_cost" in assessment and assessment["estimated_cost"]:
                    costs.append(assessment["estimated_cost"])
                if "confidence" in assessment:
                    confidences.append(assessment["confidence"])
        
        primary_damage_type = max(set(damage_types), key=damage_types.count) if damage_types else "unknown"
        
        severity_order = {"minor": 1, "moderate": 2, "severe": 3, "total": 4}
        max_severity = max(severities, key=lambda s: severity_order.get(s.lower(), 0)) if severities else "moderate"
        
        avg_cost = sum(costs) / len(costs) if costs else None
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.8
        
        return {
            "damage_type": primary_damage_type,
            "affected_parts": list(affected_parts),
            "severity": max_severity,
            "estimated_cost": avg_cost,
            "confidence": avg_confidence,
            "image_count": len(results)
        }
    
    def _mock_analysis(
        self,
        claim_id: str,
        images: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Mock analysis when ADK is not available."""
        return {
            "summary": f"Mock analysis of {len(images)} image(s)",
            "damage_assessment": {
                "damage_type": "collision",
                "affected_parts": ["front_bumper", "hood"],
                "severity": "moderate",
                "estimated_cost": 3500.00,
                "confidence": 0.89
            },
            "valid": True,
            "confidence": 0.89,
            "analysis_id": f"mock_img_{claim_id}"
        }
