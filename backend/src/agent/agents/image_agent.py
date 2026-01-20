"""
Image Agent - Analyzes images (damage photos, scene photos).

Uses Gemini API for image analysis and damage assessment.
"""

import os
from typing import Dict, Any, List
from pathlib import Path

try:
    import google.genai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class ImageAgent:
    """Specialized agent for image analysis."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY")
        self.model_name = os.getenv("AGENT_MODEL", "gemini-2.0-flash")
        self.client = None
        
        if self.api_key and GEMINI_AVAILABLE:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Failed to initialize Gemini for ImageAgent: {e}")
                self.client = None
    
    async def analyze(
        self,
        claim_id: str,
        images: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze images for a claim.
        
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
        
        if not self.client:
            # Fallback to mock analysis
            return self._mock_analysis(claim_id, images)
        
        # Analyze each image with Gemini
        results = []
        for img in images:
            file_path = img.get("file_path")
            if not file_path or not Path(file_path).exists():
                continue
            
            try:
                result = await self._analyze_image(file_path, claim_id)
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
    
    async def _analyze_image(
        self,
        file_path: str,
        claim_id: str
    ) -> Dict[str, Any]:
        """Analyze a single image using Gemini."""
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
            
            # Create prompt
            prompt = """Analyze this insurance claim image and assess:
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
            
            # Use Gemini to analyze with new API
            from google.genai import types
            
            # Use async client
            aio_client = self.client.aio
            
            # Create content parts
            contents = [
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=file_data, mime_type=mime_type)
            ]
            
            # Use async API
            response = await aio_client.models.generate_content(
                model=self.model_name,
                contents=contents
            )
            
            # Parse response
            if hasattr(response, 'text'):
                text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                text = response.candidates[0].content.parts[0].text
            else:
                text = str(response)
            
            # Try to extract JSON from response
            import json
            import re
            
            # Look for JSON in the response
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if json_match:
                try:
                    assessment = json.loads(json_match.group())
                except:
                    assessment = self._parse_text_response(text)
            else:
                assessment = self._parse_text_response(text)
            
            return {
                "valid": assessment.get("valid", True),
                "damage_assessment": assessment,
                "confidence": assessment.get("confidence", 0.8),
                "notes": assessment.get("notes", "")
            }
            
        except Exception as e:
            print(f"Error in image analysis: {e}")
            return {
                "valid": False,
                "error": str(e),
                "confidence": 0.0
            }
    
    def _parse_text_response(self, text: str) -> Dict[str, Any]:
        """Parse text response when JSON extraction fails."""
        # Fallback parsing - try to extract key information
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
        
        # Collect all damage types and affected parts
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
        
        # Determine most common damage type
        primary_damage_type = max(set(damage_types), key=damage_types.count) if damage_types else "unknown"
        
        # Determine most severe severity
        severity_order = {"minor": 1, "moderate": 2, "severe": 3, "total": 4}
        max_severity = max(severities, key=lambda s: severity_order.get(s.lower(), 0)) if severities else "moderate"
        
        # Calculate average cost
        avg_cost = sum(costs) / len(costs) if costs else None
        
        # Calculate average confidence
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
        """Mock analysis when Gemini is not available."""
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
