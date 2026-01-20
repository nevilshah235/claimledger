"""
Fraud Agent - Detects fraud patterns and risk factors.

Analyzes claim patterns, consistency, and fraud indicators.
"""

import os
from typing import Dict, Any, List
from decimal import Decimal

try:
    import google.genai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class FraudAgent:
    """Specialized agent for fraud detection."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY")
        self.model_name = os.getenv("AGENT_MODEL", "gemini-2.0-flash")
        self.client = None
        
        if self.api_key and GEMINI_AVAILABLE:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Failed to initialize Gemini for FraudAgent: {e}")
                self.client = None
    
    async def analyze(
        self,
        claim_id: str,
        claim_amount: Decimal,
        claimant_address: str,
        evidence: List[Dict[str, Any]],
        agent_results: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze claim for fraud indicators.
        
        Args:
            claim_id: Claim identifier
            claim_amount: Claim amount
            claimant_address: Claimant wallet address
            evidence: List of evidence files
            agent_results: Results from other agents (document, image)
            
        Returns:
            {
                "fraud_score": float (0.0-1.0, lower is better),
                "risk_level": str (LOW, MEDIUM, HIGH),
                "indicators": list of fraud indicators,
                "confidence": float,
                "check_id": str
            }
        """
        if not self.client:
            # Fallback to mock analysis
            return self._mock_analysis(claim_id)
        
        # Build context for fraud analysis
        context = self._build_context(
            claim_id, claim_amount, claimant_address, evidence, agent_results
        )
        
        try:
            result = await self._analyze_fraud(context)
            return result
        except Exception as e:
            print(f"Error in fraud analysis: {e}")
            return {
                "fraud_score": 0.5,  # Neutral on error
                "risk_level": "MEDIUM",
                "indicators": [f"Analysis error: {str(e)}"],
                "confidence": 0.5,
                "check_id": f"fraud_{claim_id}"
            }
    
    def _build_context(
        self,
        claim_id: str,
        claim_amount: Decimal,
        claimant_address: str,
        evidence: List[Dict[str, Any]],
        agent_results: Dict[str, Any]
    ) -> str:
        """Build context string for fraud analysis."""
        context_parts = [
            f"Claim ID: {claim_id}",
            f"Claim Amount: ${float(claim_amount):,.2f}",
            f"Claimant Address: {claimant_address}",
            f"Evidence Files: {len(evidence)}"
        ]
        
        # Add document analysis results
        if agent_results and "document" in agent_results:
            doc_result = agent_results["document"]
            if doc_result.get("extracted_data"):
                data = doc_result["extracted_data"]
                context_parts.append(
                    f"Document Analysis: {data.get('document_type', 'unknown')}, "
                    f"Amount: ${data.get('amount', 0):,.2f}, "
                    f"Vendor: {data.get('vendor', 'unknown')}"
                )
        
        # Add image analysis results
        if agent_results and "image" in agent_results:
            img_result = agent_results["image"]
            if img_result.get("damage_assessment"):
                assessment = img_result["damage_assessment"]
                estimated_cost = assessment.get('estimated_cost')
                cost_str = f"${estimated_cost:,.2f}" if estimated_cost is not None else "N/A"
                context_parts.append(
                    f"Image Analysis: {assessment.get('damage_type', 'unknown')}, "
                    f"Severity: {assessment.get('severity', 'unknown')}, "
                    f"Estimated Cost: {cost_str}"
                )
        
        return "\n".join(context_parts)
    
    async def _analyze_fraud(self, context: str) -> Dict[str, Any]:
        """Analyze fraud using Gemini."""
        prompt = f"""Analyze this insurance claim for fraud indicators:

{context}

Check for:
1. Inconsistencies between claim amount and evidence
2. Suspicious patterns (timing, amounts, frequency)
3. Evidence authenticity concerns
4. Unusual claim characteristics

Return a JSON object with:
- fraud_score: float (0.0-1.0, where 0.0 = no fraud, 1.0 = high fraud risk)
- risk_level: string (LOW if score < 0.3, MEDIUM if 0.3-0.7, HIGH if > 0.7)
- indicators: array of strings (specific fraud indicators found, empty if none)
- confidence: float (0.0-1.0, confidence in the analysis)
- notes: string (explanation of the assessment)"""
        
        # Use new API with async client
        from google.genai import types
        aio_client = self.client.aio
        
        # Use async API
        response = await aio_client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        
        # Parse response
        if hasattr(response, 'text'):
            text = response.text
        elif hasattr(response, 'candidates') and response.candidates:
            text = response.candidates[0].content.parts[0].text
        else:
            text = str(response)
        
        # Parse response
        import json
        import re
        
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
            except:
                result = self._parse_text_response(text)
        else:
            result = self._parse_text_response(text)
        
        # Ensure fraud_score is in valid range
        fraud_score = max(0.0, min(1.0, float(result.get("fraud_score", 0.5))))
        
        # Determine risk level
        if fraud_score < 0.3:
            risk_level = "LOW"
        elif fraud_score < 0.7:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"
        
        return {
            "fraud_score": fraud_score,
            "risk_level": risk_level,
            "indicators": result.get("indicators", []),
            "confidence": result.get("confidence", 0.8),
            "notes": result.get("notes", ""),
            "check_id": f"fraud_{context.split()[1]}"  # Extract claim_id from context
        }
    
    def _parse_text_response(self, text: str) -> Dict[str, Any]:
        """Parse text response when JSON extraction fails."""
        # Fallback parsing
        fraud_score = 0.1  # Default to low fraud risk
        if "suspicious" in text.lower() or "fraud" in text.lower():
            fraud_score = 0.5
        
        return {
            "fraud_score": fraud_score,
            "risk_level": "LOW" if fraud_score < 0.3 else ("MEDIUM" if fraud_score < 0.7 else "HIGH"),
            "indicators": [],
            "confidence": 0.7,
            "notes": text
        }
    
    def _mock_analysis(self, claim_id: str) -> Dict[str, Any]:
        """Mock analysis when Gemini is not available."""
        return {
            "fraud_score": 0.05,
            "risk_level": "LOW",
            "indicators": [],
            "confidence": 0.85,
            "check_id": f"mock_fraud_{claim_id}"
        }
