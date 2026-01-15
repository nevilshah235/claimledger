"""
ADK Orchestrator Agent - Main decision-making agent that autonomously calls tools.

This agent orchestrates the claim evaluation by:
1. Calling verification tools (verify_document, verify_image, verify_fraud) autonomously
2. Making decisions based on confidence thresholds
3. Requesting human review when needed
4. Requesting additional data when evidence is insufficient
"""

import os
from typing import Dict, Any, List, Optional
from decimal import Decimal

try:
    from google.adk.agents import LlmAgent
    from google.genai import types
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    LlmAgent = None


class ADKOrchestratorAgent:
    """ADK-based orchestrator agent that autonomously calls tools and makes decisions."""
    
    # Confidence thresholds
    AUTO_APPROVE_THRESHOLD = 0.95  # >= 95% confidence: auto-approve
    HIGH_CONFIDENCE_THRESHOLD = 0.85  # >= 85% confidence: can approve with human review
    MEDIUM_CONFIDENCE_THRESHOLD = 0.70  # >= 70% confidence: needs human review
    LOW_CONFIDENCE_THRESHOLD = 0.50  # < 50% confidence: request more data
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = os.getenv("AGENT_MODEL", "gemini-2.0-flash-exp")
        self.agent = None
        
        if not ADK_AVAILABLE:
            print("⚠️  ADK not available, OrchestratorAgent will use fallback")
            return
        
        if not self.api_key:
            print("⚠️  Warning: GOOGLE_AI_API_KEY or GOOGLE_API_KEY not set")
            return
        
        try:
            # Import ADK tools
            from ..adk_tools import get_adk_tools
            
            # Create ADK LlmAgent with tool-calling capabilities
            self.agent = LlmAgent(
                model=self.model_name,
                name="orchestrator_agent",
                description="Main orchestrator agent that evaluates insurance claims by calling verification tools and making decisions",
                instruction="""You are an insurance claim evaluation orchestrator agent.

Your job is to evaluate insurance claims by calling verification tools and making decisions based on confidence thresholds.

**Process:**
1. For each claim, you MUST call the appropriate verification tools:
   - verify_document(claim_id, document_path) - Verify documents ($0.10 USDC)
   - verify_image(claim_id, image_path) - Analyze images ($0.15 USDC)
   - verify_fraud(claim_id) - Check fraud indicators ($0.10 USDC)

2. After collecting all verification results, analyze the evidence and calculate overall confidence.

3. Make a decision based on confidence thresholds:
   - confidence >= 0.95 AND no contradictions AND fraud_risk < 0.3:
     → Decision: AUTO_APPROVED
     → Call approve_claim(claim_id, amount, recipient) to settle automatically
   
   - confidence >= 0.85 AND no major contradictions:
     → Decision: APPROVED_WITH_REVIEW
     → Flag for human review before settlement
   
   - confidence >= 0.70:
     → Decision: NEEDS_REVIEW
     → Requires human review, do not auto-approve
   
   - confidence >= 0.50:
     → Decision: NEEDS_MORE_DATA
     → Request additional evidence from claimant
   
   - confidence < 0.50:
     → Decision: INSUFFICIENT_DATA
     → Request more data or flag for manual investigation

**Important Rules:**
- ALWAYS call verify_document, verify_image, and verify_fraud tools when evidence is available
- Each tool call costs USDC (handled automatically via x402)
- Only call approve_claim if confidence >= 0.95, no contradictions, and fraud_risk < 0.3
- If confidence is below thresholds, clearly state what additional data is needed
- Be transparent about your reasoning and confidence level

**Output Format:**
Return a JSON object with:
- decision: string (AUTO_APPROVED, APPROVED_WITH_REVIEW, NEEDS_REVIEW, NEEDS_MORE_DATA, INSUFFICIENT_DATA)
- confidence: float (0.0-1.0)
- reasoning: string (detailed explanation)
- tool_results: object (results from all tool calls)
- requested_data: array of strings (what additional data is needed, empty if none)
- human_review_required: boolean (true if human review is needed)
- review_reasons: array of strings (why human review is needed, empty if none)""",
                tools=get_adk_tools(),  # Include all ADK tools for autonomous calling
            )
        except Exception as e:
            print(f"Failed to initialize ADK OrchestratorAgent: {e}")
            self.agent = None
    
    async def evaluate_claim(
        self,
        claim_id: str,
        claim_amount: Decimal,
        claimant_address: str,
        evidence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate a claim by autonomously calling tools and making decisions.
        
        Args:
            claim_id: Claim identifier
            claim_amount: Claim amount in USDC
            claimant_address: Claimant wallet address
            evidence: List of evidence dicts with file_type and file_path
            
        Returns:
            {
                "decision": str,
                "confidence": float,
                "reasoning": str,
                "tool_results": dict,
                "requested_data": list,
                "human_review_required": bool,
                "review_reasons": list,
                "auto_settled": bool,
                "tx_hash": str | None
            }
        """
        if not self.agent:
            # Fallback to rule-based evaluation
            return await self._fallback_evaluation(claim_id, claim_amount, claimant_address, evidence)
        
        try:
            return await self._ai_evaluation_with_tools(claim_id, claim_amount, claimant_address, evidence)
        except Exception as e:
            print(f"Error in ADK orchestrator agent: {e}")
            return await self._fallback_evaluation(claim_id, claim_amount, claimant_address, evidence)
    
    async def _ai_evaluation_with_tools(
        self,
        claim_id: str,
        claim_amount: Decimal,
        claimant_address: str,
        evidence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use ADK agent to autonomously call tools and make decisions."""
        from ..adk_runtime import get_adk_runtime
        
        # Build evidence context
        evidence_context = self._build_evidence_context(evidence)
        
        prompt = f"""Evaluate this insurance claim:

Claim ID: {claim_id}
Claim Amount: ${float(claim_amount):,.2f}
Claimant Address: {claimant_address}

Available Evidence:
{evidence_context}

**Your Task:**
1. Call the appropriate verification tools for each piece of evidence:
   - For documents: call verify_document(claim_id, document_path)
   - For images: call verify_image(claim_id, image_path)
   - Always call verify_fraud(claim_id) to check fraud indicators

2. After collecting all tool results, analyze the evidence and calculate overall confidence.

3. Make a decision based on confidence thresholds:
   - >= 0.95 + no contradictions + fraud_risk < 0.3 → AUTO_APPROVED (call approve_claim)
   - >= 0.85 → APPROVED_WITH_REVIEW (human review required)
   - >= 0.70 → NEEDS_REVIEW (human review required)
   - >= 0.50 → NEEDS_MORE_DATA (request additional evidence)
   - < 0.50 → INSUFFICIENT_DATA (request more data or manual investigation)

4. Return a JSON object with your decision, confidence, reasoning, and any requested data.

Remember: You MUST call the verification tools - they handle payments automatically via x402."""
        
        # Create user message
        user_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        )
        
        # Run ADK agent (it will autonomously call tools)
        runtime = get_adk_runtime()
        runner = runtime.create_runner(
            app_name="claimledger",
            agent=self.agent
        )
        
        response_text = ""
        tool_results = {}
        async for event in runner.run_async(
            user_id=f"claim_{claim_id}",
            session_id=f"orchestrator_{claim_id}",
            new_message=user_message
        ):
            # Collect tool call results
            if hasattr(event, 'tool_calls') and event.tool_calls:
                for tool_call in event.tool_calls:
                    tool_name = tool_call.get('name', 'unknown')
                    tool_result = tool_call.get('result', {})
                    tool_results[tool_name] = tool_result
            
            # Collect text response
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
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
            except:
                result = self._parse_text_response(response_text, tool_results)
        else:
            result = self._parse_text_response(response_text, tool_results)
        
        # Process decision based on confidence
        confidence = float(result.get("confidence", 0.5))
        decision = result.get("decision", "NEEDS_REVIEW")
        contradictions = result.get("contradictions", [])
        fraud_risk = float(result.get("fraud_risk", 0.5))
        
        # Determine if auto-settlement occurred
        auto_settled = False
        tx_hash = None
        if "approve_claim" in tool_results:
            approve_result = tool_results["approve_claim"]
            if approve_result.get("success"):
                auto_settled = True
                tx_hash = approve_result.get("tx_hash")
        
        # Determine human review requirement
        human_review_required = decision in [
            "APPROVED_WITH_REVIEW",
            "NEEDS_REVIEW",
            "NEEDS_MORE_DATA",
            "INSUFFICIENT_DATA"
        ]
        
        # Build review reasons
        review_reasons = []
        if confidence < self.AUTO_APPROVE_THRESHOLD:
            review_reasons.append(f"Confidence {confidence:.2%} below auto-approval threshold ({self.AUTO_APPROVE_THRESHOLD:.2%})")
        if contradictions:
            review_reasons.append(f"{len(contradictions)} contradiction(s) detected")
        if fraud_risk >= 0.3:
            review_reasons.append(f"Fraud risk {fraud_risk:.2f} exceeds threshold (0.3)")
        
        requested_data = result.get("requested_data", [])
        if requested_data:
            review_reasons.append(f"Additional data requested: {', '.join(requested_data)}")
        
        return {
            "decision": decision,
            "confidence": max(0.0, min(1.0, confidence)),
            "reasoning": result.get("reasoning", ""),
            "tool_results": tool_results,
            "requested_data": requested_data,
            "human_review_required": human_review_required,
            "review_reasons": review_reasons,
            "auto_settled": auto_settled,
            "tx_hash": tx_hash,
            "contradictions": contradictions,
            "fraud_risk": fraud_risk
        }
    
    def _build_evidence_context(self, evidence: List[Dict[str, Any]]) -> str:
        """Build evidence context string."""
        if not evidence:
            return "No evidence provided"
        
        context_parts = []
        for i, ev in enumerate(evidence, 1):
            file_type = ev.get("file_type", "unknown")
            file_path = ev.get("file_path", "unknown")
            context_parts.append(f"{i}. {file_type.upper()}: {file_path}")
        
        return "\n".join(context_parts)
    
    def _parse_text_response(
        self,
        text: str,
        tool_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse text response when JSON extraction fails."""
        # Extract confidence if mentioned
        import re
        confidence_match = re.search(r'confidence[:\s]+([0-9.]+)', text, re.IGNORECASE)
        confidence = float(confidence_match.group(1)) if confidence_match else 0.5
        
        # Determine decision based on confidence
        if confidence >= self.AUTO_APPROVE_THRESHOLD:
            decision = "AUTO_APPROVED"
        elif confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            decision = "APPROVED_WITH_REVIEW"
        elif confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            decision = "NEEDS_REVIEW"
        elif confidence >= self.LOW_CONFIDENCE_THRESHOLD:
            decision = "NEEDS_MORE_DATA"
        else:
            decision = "INSUFFICIENT_DATA"
        
        return {
            "decision": decision,
            "confidence": confidence,
            "reasoning": text[:500],  # First 500 chars
            "requested_data": [],
            "contradictions": [],
            "fraud_risk": 0.5
        }
    
    async def _fallback_evaluation(
        self,
        claim_id: str,
        claim_amount: Decimal,
        claimant_address: str,
        evidence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Fallback rule-based evaluation when AI is not available."""
        # Simple rule-based evaluation
        documents = [e for e in evidence if e.get("file_type") == "document"]
        images = [e for e in evidence if e.get("file_type") == "image"]
        
        # Calculate confidence based on available evidence
        confidence = 0.5  # Base confidence
        if documents:
            confidence += 0.2
        if images:
            confidence += 0.2
        if len(documents) + len(images) >= 2:
            confidence += 0.1
        
        confidence = min(1.0, confidence)
        
        # Determine decision
        if confidence >= self.AUTO_APPROVE_THRESHOLD:
            decision = "AUTO_APPROVED"
        elif confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            decision = "APPROVED_WITH_REVIEW"
        elif confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            decision = "NEEDS_REVIEW"
        elif confidence >= self.LOW_CONFIDENCE_THRESHOLD:
            decision = "NEEDS_MORE_DATA"
        else:
            decision = "INSUFFICIENT_DATA"
        
        requested_data = []
        if not documents:
            requested_data.append("document")
        if not images:
            requested_data.append("image")
        
        return {
            "decision": decision,
            "confidence": confidence,
            "reasoning": f"Rule-based evaluation: {len(documents)} document(s), {len(images)} image(s)",
            "tool_results": {},
            "requested_data": requested_data,
            "human_review_required": decision != "AUTO_APPROVED",
            "review_reasons": [f"Confidence {confidence:.2%} below auto-approval threshold"] if confidence < self.AUTO_APPROVE_THRESHOLD else [],
            "auto_settled": False,
            "tx_hash": None,
            "contradictions": [],
            "fraud_risk": 0.5
        }
