"""
Reasoning Agent - Correlates evidence, detects contradictions, calculates confidence.

This agent takes results from all specialized agents and performs final reasoning.
"""

import os
from typing import Dict, Any, List
from decimal import Decimal

try:
    import google.genai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class ReasoningAgent:
    """Specialized agent for evidence correlation and reasoning."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY")
        self.model_name = os.getenv("AGENT_MODEL", "gemini-2.0-flash")
        self.client = None
        
        if self.api_key and GEMINI_AVAILABLE:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Failed to initialize Gemini for ReasoningAgent: {e}")
                self.client = None
    
    async def reason(
        self,
        claim_id: str,
        claim_amount: Decimal,
        agent_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform reasoning on agent results.
        
        Args:
            claim_id: Claim identifier
            claim_amount: Claim amount
            agent_results: Results from all specialized agents
            
        Returns:
            {
                "final_confidence": float (0.0-1.0),
                "contradictions": list of contradictions found,
                "fraud_risk": float (0.0-1.0),
                "missing_evidence": list of missing evidence types,
                "reasoning": str (explanation),
                "evidence_gaps": list of gaps
            }
        """
        if not self.client:
            # Fallback to rule-based reasoning
            return self._rule_based_reasoning(claim_id, claim_amount, agent_results)
        
        try:
            result = await self._ai_reasoning(claim_id, claim_amount, agent_results)
            return result
        except Exception as e:
            print(f"Error in AI reasoning: {e}")
            # Fallback to rule-based
            return self._rule_based_reasoning(claim_id, claim_amount, agent_results)
    
    async def _ai_reasoning(
        self,
        claim_id: str,
        claim_amount: Decimal,
        agent_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use Gemini for advanced reasoning."""
        # Build context
        context = self._build_reasoning_context(claim_id, claim_amount, agent_results)
        
        prompt = f"""You are an insurance claim reasoning agent. Analyze the following agent results and provide a comprehensive assessment:

{context}

Your task:
1. Correlate evidence from all agents
2. Detect contradictions between different evidence sources
3. Calculate overall confidence (0.0-1.0)
4. Identify missing evidence that would improve confidence
5. Assess fraud risk based on all evidence

Return a JSON object with:
- final_confidence: float (0.0-1.0, overall confidence in claim validity)
- contradictions: array of strings (any contradictions found, empty if none)
- fraud_risk: float (0.0-1.0, overall fraud risk assessment)
- missing_evidence: array of strings (types of evidence that would help, empty if sufficient)
- reasoning: string (detailed explanation of your assessment)
- evidence_gaps: array of strings (specific gaps in evidence, empty if none)"""
        
        # Use new API with async client
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
                result = self._parse_text_response(text, agent_results)
        else:
            result = self._parse_text_response(text, agent_results)
        
        # Ensure values are in valid ranges
        final_confidence = max(0.0, min(1.0, float(result.get("final_confidence", 0.5))))
        fraud_risk = max(0.0, min(1.0, float(result.get("fraud_risk", 0.5))))
        
        return {
            "final_confidence": final_confidence,
            "contradictions": result.get("contradictions", []),
            "fraud_risk": fraud_risk,
            "missing_evidence": result.get("missing_evidence", []),
            "reasoning": result.get("reasoning", ""),
            "evidence_gaps": result.get("evidence_gaps", [])
        }
    
    def _build_reasoning_context(
        self,
        claim_id: str,
        claim_amount: Decimal,
        agent_results: Dict[str, Any]
    ) -> str:
        """Build context string for reasoning."""
        context_parts = [
            f"Claim ID: {claim_id}",
            f"Claim Amount: ${float(claim_amount):,.2f}",
            "",
            "Agent Results:"
        ]
        
        # Document agent results
        if "document" in agent_results:
            doc_result = agent_results["document"]
            context_parts.append(f"\nDocument Agent:")
            context_parts.append(f"  Valid: {doc_result.get('valid', False)}")
            context_parts.append(f"  Confidence: {doc_result.get('confidence', 0.0):.2f}")
            if doc_result.get("extracted_data"):
                data = doc_result["extracted_data"]
                context_parts.append(f"  Type: {data.get('document_type', 'unknown')}")
                amount = data.get('amount')
                amount_str = f"${amount:,.2f}" if amount is not None else "N/A"
                context_parts.append(f"  Amount: {amount_str}")
                context_parts.append(f"  Vendor: {data.get('vendor', 'unknown')}")
        
        # Image agent results
        if "image" in agent_results:
            img_result = agent_results["image"]
            context_parts.append(f"\nImage Agent:")
            context_parts.append(f"  Valid: {img_result.get('valid', False)}")
            context_parts.append(f"  Confidence: {img_result.get('confidence', 0.0):.2f}")
            if img_result.get("damage_assessment"):
                assessment = img_result["damage_assessment"]
                estimated_cost = assessment.get('estimated_cost')
                cost_str = f"${estimated_cost:,.2f}" if estimated_cost is not None else "N/A"
                context_parts.append(f"  Damage Type: {assessment.get('damage_type', 'unknown')}")
                context_parts.append(f"  Severity: {assessment.get('severity', 'unknown')}")
                context_parts.append(f"  Estimated Cost: {cost_str}")
        
        # Fraud agent results
        if "fraud" in agent_results:
            fraud_result = agent_results["fraud"]
            context_parts.append(f"\nFraud Agent:")
            context_parts.append(f"  Fraud Score: {fraud_result.get('fraud_score', 0.0):.2f}")
            context_parts.append(f"  Risk Level: {fraud_result.get('risk_level', 'UNKNOWN')}")
            if fraud_result.get("indicators"):
                context_parts.append(f"  Indicators: {', '.join(fraud_result['indicators'])}")
        
        return "\n".join(context_parts)
    
    def _parse_text_response(
        self,
        text: str,
        agent_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse text response when JSON extraction fails."""
        # Fallback to rule-based reasoning
        return self._rule_based_reasoning(
            "unknown",  # claim_id
            Decimal("0"),  # claim_amount
            agent_results
        )
    
    def _rule_based_reasoning(
        self,
        claim_id: str,
        claim_amount: Decimal,
        agent_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Rule-based reasoning when AI is not available."""
        contradictions = []
        missing_evidence = []
        evidence_gaps = []
        
        # Check document results
        doc_result = agent_results.get("document", {})
        doc_valid = doc_result.get("valid", False)
        doc_amount = None
        if doc_result.get("extracted_data"):
            doc_amount = doc_result["extracted_data"].get("amount")
        
        # Check image results
        img_result = agent_results.get("image", {})
        img_valid = img_result.get("valid", False)
        img_cost = None
        if img_result.get("damage_assessment"):
            img_cost = img_result["damage_assessment"].get("estimated_cost")
        
        # Check fraud results
        fraud_result = agent_results.get("fraud", {})
        fraud_score = fraud_result.get("fraud_score", 0.5)
        fraud_risk = fraud_score
        
        # Detect contradictions
        if doc_amount is not None and img_cost is not None:
            # Check if amounts are consistent (within 20% tolerance)
            diff = abs(float(doc_amount) - float(img_cost))
            avg = (float(doc_amount) + float(img_cost)) / 2
            if avg > 0 and (diff / avg) > 0.2:
                doc_amount_str = f"${doc_amount:,.2f}"
                img_cost_str = f"${img_cost:,.2f}"
                contradictions.append(
                    f"Document amount ({doc_amount_str}) differs significantly from "
                    f"image estimated cost ({img_cost_str})"
                )
        
        if doc_amount is not None and float(claim_amount):
            # Check if claim amount matches document
            diff = abs(float(doc_amount) - float(claim_amount))
            if diff > 100:  # More than $100 difference
                claim_amount_str = f"${float(claim_amount):,.2f}"
                doc_amount_str = f"${doc_amount:,.2f}"
                contradictions.append(
                    f"Claim amount ({claim_amount_str}) differs from "
                    f"document amount ({doc_amount_str})"
                )
        
        # Check for missing evidence
        if not doc_valid:
            missing_evidence.append("valid_document")
            evidence_gaps.append("No valid document verification")
        
        if not img_valid:
            missing_evidence.append("valid_image")
            evidence_gaps.append("No valid image analysis")
        
        # Calculate confidence
        confidence_scores = []
        
        if doc_valid:
            confidence_scores.append(doc_result.get("confidence", 0.8))
        else:
            confidence_scores.append(0.3)
        
        if img_valid:
            confidence_scores.append(img_result.get("confidence", 0.8))
        else:
            confidence_scores.append(0.3)
        
        # Fraud score affects confidence (lower fraud = higher confidence)
        fraud_confidence = 1.0 - fraud_risk
        confidence_scores.append(fraud_confidence)
        
        # Weighted average (document: 40%, image: 30%, fraud: 30%)
        if confidence_scores:
            final_confidence = (
                confidence_scores[0] * 0.4 +
                confidence_scores[1] * 0.3 +
                confidence_scores[2] * 0.3
            )
        else:
            final_confidence = 0.5
        
        # Penalize for contradictions
        if contradictions:
            final_confidence *= 0.8  # Reduce confidence by 20%
        
        # Build reasoning
        reasoning_parts = []
        if doc_valid and img_valid:
            reasoning_parts.append("Both document and image evidence are valid.")
        elif doc_valid:
            reasoning_parts.append("Document evidence is valid, but image analysis is missing or invalid.")
        elif img_valid:
            reasoning_parts.append("Image evidence is valid, but document verification is missing or invalid.")
        else:
            reasoning_parts.append("Both document and image evidence are missing or invalid.")
        
        if contradictions:
            reasoning_parts.append(f"Found {len(contradictions)} contradiction(s) that need review.")
        
        if fraud_risk < 0.3:
            reasoning_parts.append("Fraud risk is low.")
        elif fraud_risk < 0.7:
            reasoning_parts.append("Fraud risk is moderate.")
        else:
            reasoning_parts.append("Fraud risk is high.")
        
        reasoning = " ".join(reasoning_parts)
        
        return {
            "final_confidence": max(0.0, min(1.0, final_confidence)),
            "contradictions": contradictions,
            "fraud_risk": fraud_risk,
            "missing_evidence": missing_evidence,
            "reasoning": reasoning,
            "evidence_gaps": evidence_gaps
        }
