"""
Insurance Claim Evaluation Agent.
Uses Google Agents Framework with Gemini for multimodal claim evaluation.

Agent responsibilities:
- Reason over multimodal claim context
- Call explicit tools (verify_document, verify_image, verify_fraud)
- Return structured JSON decision
- Only approve if confidence >= 0.85

Uses Google Agents Framework with Gemini.
Uses Circle Gateway for x402 micropayments (via tools).
"""

import os
import json
from typing import Dict, Any, List, Optional
from decimal import Decimal

from .tools import (
    verify_document,
    verify_image,
    verify_fraud,
    approve_claim,
    TOOL_DEFINITIONS
)


# Agent configuration
GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY")
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini-2.0-flash")

# System instruction for the agent
SYSTEM_INSTRUCTION = """You are an insurance claim evaluator agent.

Your job is to evaluate insurance claims using the provided tools and make a decision.

**Process:**
1. First, call verify_document to verify the submitted documents (invoices, receipts)
2. Then, call verify_image to analyze any damage photos
3. Finally, call verify_fraud to check for fraud indicators

**Decision Rules:**
- Calculate overall confidence based on tool results
- If confidence >= 0.85 → Decision: APPROVED
- If confidence < 0.85 → Decision: NEEDS_REVIEW

**Important:**
- Each tool call costs USDC (micropayment via x402)
- Only call approve_claim if decision is APPROVED
- Always return a structured JSON response

**Output Format:**
{
    "decision": "APPROVED | NEEDS_REVIEW | REJECTED",
    "confidence": 0.0-1.0,
    "approved_amount": number or null,
    "reasoning": "Detailed explanation of the decision"
}
"""


class ClaimEvaluationAgent:
    """
    Agent for evaluating insurance claims.
    
    Uses Google Agents Framework with Gemini model.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GOOGLE_AI_API_KEY
        self.model = AGENT_MODEL
        
        # Tool mapping
        self.tools = {
            "verify_document": verify_document,
            "verify_image": verify_image,
            "verify_fraud": verify_fraud,
            "approve_claim": approve_claim
        }
        
        # Initialize Google AI client if API key available
        self.client = None
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(
                    model_name=self.model,
                    system_instruction=SYSTEM_INSTRUCTION
                )
            except ImportError:
                print("google-generativeai not installed, using mock mode")
            except Exception as e:
                print(f"Failed to initialize Gemini: {e}")
    
    async def evaluate(
        self,
        claim_id: str,
        claim_amount: Decimal,
        claimant_address: str,
        evidence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate a claim using the AI agent.
        
        Args:
            claim_id: Unique claim identifier
            claim_amount: Requested claim amount
            claimant_address: Claimant's wallet address
            evidence: List of evidence files with paths and types
            
        Returns:
            {
                "decision": str,
                "confidence": float,
                "approved_amount": float or None,
                "reasoning": str,
                "processing_costs": float
            }
        """
        if self.client:
            return await self._evaluate_with_gemini(
                claim_id, claim_amount, claimant_address, evidence
            )
        else:
            return await self._evaluate_mock(
                claim_id, claim_amount, claimant_address, evidence
            )
    
    async def _evaluate_with_gemini(
        self,
        claim_id: str,
        claim_amount: Decimal,
        claimant_address: str,
        evidence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate using actual Gemini model.
        
        TODO: Implement full Google Agents Framework integration.
        """
        # Build prompt with claim context
        prompt = f"""
        Evaluate this insurance claim:
        
        Claim ID: {claim_id}
        Claim Amount: ${float(claim_amount):,.2f}
        Claimant Address: {claimant_address}
        Evidence Files: {len(evidence)} files
        
        Evidence details:
        {json.dumps(evidence, indent=2)}
        
        Use the available tools to verify the claim and make a decision.
        """
        
        # For now, use mock evaluation
        # TODO: Implement proper tool calling with Gemini
        return await self._evaluate_mock(
            claim_id, claim_amount, claimant_address, evidence
        )
    
    async def _evaluate_mock(
        self,
        claim_id: str,
        claim_amount: Decimal,
        claimant_address: str,
        evidence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Mock evaluation for demo purposes.
        
        Simulates the agent calling tools and making a decision.
        """
        total_cost = Decimal("0")
        tool_results = []
        
        # Find document and image evidence
        document_path = None
        image_path = None
        
        for e in evidence:
            if e.get("file_type") == "document":
                document_path = e.get("file_path")
            elif e.get("file_type") == "image":
                image_path = e.get("file_path")
        
        # Call verify_document
        if document_path:
            doc_result = await verify_document(claim_id, document_path)
            tool_results.append(("verify_document", doc_result))
            total_cost += Decimal(str(doc_result.get("cost", 0.10)))
        
        # Call verify_image
        if image_path:
            img_result = await verify_image(claim_id, image_path)
            tool_results.append(("verify_image", img_result))
            total_cost += Decimal(str(img_result.get("cost", 0.15)))
        
        # Call verify_fraud
        fraud_result = await verify_fraud(claim_id)
        tool_results.append(("verify_fraud", fraud_result))
        total_cost += Decimal(str(fraud_result.get("cost", 0.10)))
        
        # Calculate confidence based on results
        confidence = self._calculate_confidence(tool_results)
        
        # Make decision
        if confidence >= 0.85:
            decision = "APPROVED"
            approved_amount = float(claim_amount)
        else:
            decision = "NEEDS_REVIEW"
            approved_amount = None
        
        # Build reasoning
        reasoning = self._build_reasoning(
            tool_results, confidence, decision, claim_amount
        )
        
        return {
            "decision": decision,
            "confidence": confidence,
            "approved_amount": approved_amount,
            "reasoning": reasoning,
            "processing_costs": float(total_cost),
            "tool_results": tool_results
        }
    
    def _calculate_confidence(
        self,
        tool_results: List[tuple]
    ) -> float:
        """Calculate overall confidence from tool results."""
        scores = []
        
        for tool_name, result in tool_results:
            if not result.get("success", False):
                scores.append(0.0)
                continue
            
            if tool_name == "verify_document":
                # Document validity contributes 40%
                if result.get("valid", False):
                    scores.append(0.95)
                else:
                    scores.append(0.3)
            
            elif tool_name == "verify_image":
                # Image analysis contributes 30%
                if result.get("valid", False):
                    assessment = result.get("damage_assessment", {})
                    scores.append(assessment.get("confidence", 0.85))
                else:
                    scores.append(0.3)
            
            elif tool_name == "verify_fraud":
                # Fraud check contributes 30%
                fraud_score = result.get("fraud_score", 0.5)
                # Lower fraud score = higher confidence
                scores.append(1.0 - fraud_score)
        
        if not scores:
            return 0.0
        
        # Weighted average (simplified)
        return sum(scores) / len(scores)
    
    def _build_reasoning(
        self,
        tool_results: List[tuple],
        confidence: float,
        decision: str,
        claim_amount: Decimal
    ) -> str:
        """Build reasoning explanation from tool results."""
        parts = []
        
        for tool_name, result in tool_results:
            if tool_name == "verify_document":
                if result.get("valid"):
                    data = result.get("extracted_data", {})
                    parts.append(
                        f"Document verified: ${data.get('amount', 0):,.2f} "
                        f"{data.get('description', 'repair')} from {data.get('vendor', 'vendor')}."
                    )
                else:
                    parts.append("Document verification failed or invalid.")
            
            elif tool_name == "verify_image":
                if result.get("valid"):
                    assessment = result.get("damage_assessment", {})
                    parts.append(
                        f"Image analysis shows {assessment.get('damage_type', 'damage')} "
                        f"damage to {', '.join(assessment.get('affected_parts', ['vehicle']))}. "
                        f"Severity: {assessment.get('severity', 'unknown')}."
                    )
                else:
                    parts.append("Image analysis failed or invalid.")
            
            elif tool_name == "verify_fraud":
                fraud_score = result.get("fraud_score", 0.5)
                risk_level = result.get("risk_level", "UNKNOWN")
                parts.append(f"Fraud score: {fraud_score:.2f} ({risk_level} risk).")
        
        parts.append(f"Confidence: {confidence * 100:.0f}%.")
        parts.append(f"Recommendation: {decision}")
        
        return " ".join(parts)


# Singleton instance
_agent: Optional[ClaimEvaluationAgent] = None


def get_claim_agent() -> ClaimEvaluationAgent:
    """Get or create the claim evaluation agent singleton."""
    global _agent
    if _agent is None:
        _agent = ClaimEvaluationAgent()
    return _agent
