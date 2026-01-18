"""
ADK Reasoning Agent - Correlates evidence using ADK LlmAgent.

Converts the original ReasoningAgent to use ADK LlmAgent for evidence correlation.
"""

import os
from typing import Dict, Any, List
from decimal import Decimal

try:
    from google.adk.agents import LlmAgent
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    LlmAgent = None


class ADKReasoningAgent:
    """ADK-based agent for evidence correlation and reasoning."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = os.getenv("AGENT_MODEL", "gemini-2.0-flash")
        self.agent = None
        
        if not ADK_AVAILABLE:
            print("⚠️  ADK not available, ReasoningAgent will use fallback")
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
            
            # Create ADK LlmAgent for reasoning
            # ADK reads GOOGLE_API_KEY from environment automatically
            self.agent = LlmAgent(
                model=self.model_name,
                name="reasoning_agent",
                description="Specialized agent for correlating evidence and performing final reasoning on claim evaluation",
                instruction="""You are an insurance claim reasoning agent. Correlate evidence from all agents and detect contradictions.

**Process:**
1. Correlate evidence from document, image, and fraud agents
2. Detect contradictions between evidence sources
3. Calculate overall confidence (0.0-1.0)
4. Assess fraud risk based on all evidence
5. Identify missing evidence that would improve confidence

**Correlation Rules:**
- Document amount should match image estimated cost (within ±20%)
- Claim amount should align with extracted amounts from evidence
- Fraud indicators should be consistent across all evidence
- Confidence increases when multiple evidence sources agree

**Contradiction Detection Examples:**
Example 1: Amount mismatch
- Document: $1,000 invoice
- Image: $500 estimated damage
- Contradiction: "Document amount ($1,000) differs significantly from image estimated cost ($500)"

Example 2: Claim vs evidence mismatch
- Claim amount: $2,000
- Document amount: $1,500
- Contradiction: "Claim amount ($2,000) differs from document amount ($1,500)"

Example 3: Fraud risk inconsistency
- Document: Valid, low fraud indicators
- Fraud agent: High fraud score (0.8)
- Contradiction: "High fraud risk (0.8) contradicts valid document evidence"

**Output Format:**
Return JSON with:
- final_confidence: float (0.0-1.0)
- contradictions: array of strings (specific contradictions found)
- fraud_risk: float (0.0-1.0)
- missing_evidence: array of strings (evidence types that would help)
- reasoning: string (detailed explanation)
- evidence_gaps: array of strings (specific gaps in evidence)

Be thorough in correlation and contradiction detection.""",
                tools=[],  # Reasoning agent correlates results, no tool calling needed
            )
        except Exception as e:
            print(f"Failed to initialize ADK ReasoningAgent: {e}")
            self.agent = None
    
    async def reason(
        self,
        claim_id: str,
        claim_amount: Decimal,
        agent_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform reasoning on agent results using ADK agent.
        
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
        if not self.agent:
            # Fallback to rule-based reasoning
            return self._rule_based_reasoning(claim_id, claim_amount, agent_results)
        
        try:
            result = await self._ai_reasoning_with_adk(claim_id, claim_amount, agent_results)
            return result
        except Exception as e:
            print(f"Error in ADK reasoning: {e}")
            # Fallback to rule-based
            return self._rule_based_reasoning(claim_id, claim_amount, agent_results)
    
    async def _ai_reasoning_with_adk(
        self,
        claim_id: str,
        claim_amount: Decimal,
        agent_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use ADK agent for advanced reasoning."""
        from google.genai import types
        from ..adk_runtime import get_adk_runtime
        
        # Build context
        context = self._build_reasoning_context(claim_id, claim_amount, agent_results)
        
        prompt = f"""Analyze agent results and correlate evidence:

{context}

**Correlation Tasks:**
1. Compare amounts: document vs image vs claim_amount (flag if >20% difference)
2. Check consistency: fraud indicators vs evidence validity
3. Detect contradictions: specific mismatches between evidence sources
4. Calculate confidence: weighted average based on evidence quality and agreement
5. Assess fraud risk: combine fraud agent score with evidence inconsistencies

**Contradiction Examples:**
- Amount mismatch: "Document amount ($X) differs from image estimate ($Y)"
- Claim mismatch: "Claim amount ($X) differs from evidence amounts ($Y)"
- Fraud inconsistency: "High fraud risk contradicts valid evidence"

Return JSON with:
- final_confidence: float (0.0-1.0)
- contradictions: array of strings (specific contradictions)
- fraud_risk: float (0.0-1.0)
- missing_evidence: array of strings
- reasoning: string (detailed explanation)
- evidence_gaps: array of strings"""
        
        # Create user message
        user_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        )
        
        # Run ADK agent
        runtime = get_adk_runtime()
        runner = runtime.create_runner(
            app_name="claimledger",
            agent=self.agent
        )
        
        # Ensure session exists before using it
        user_id = f"claim_{claim_id}"
        session_id = f"reasoning_{claim_id}"
        await runtime.get_or_create_session(user_id, session_id)
        
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
        
        # Improved JSON parsing for nested JSON
        json_match = None
        patterns = [
            r'```json\s*(\{.*?\})\s*```',  # JSON code blocks
            r'```\s*(\{.*?\})\s*```',  # Code blocks without json tag
            r'\{.*\}',  # Simple pattern for nested JSON
        ]
        
        for pattern in patterns:
            json_match = re.search(pattern, response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1) if json_match.lastindex else json_match.group(0)
                try:
                    result = json.loads(json_str)
                    break
                except json.JSONDecodeError:
                    continue
        
        if not json_match or 'result' not in locals():
            result = self._parse_text_response(response_text, agent_results)
        
        # Validate against schema
        from ..adk_schemas import validate_against_schema, REASONING_SCHEMA
        is_valid, validation_errors = validate_against_schema(result, REASONING_SCHEMA)
        if not is_valid:
            print(f"   └─ ⚠️  Schema validation errors: {', '.join(validation_errors[:3])}")
            # Fix common issues
            result = self._fix_schema_issues(result, validation_errors)
        
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
    
    def _fix_schema_issues(self, data: Dict[str, Any], errors: List[str]) -> Dict[str, Any]:
        """Fix common schema validation issues."""
        # Ensure required fields exist
        if "final_confidence" not in data:
            data["final_confidence"] = 0.5
        if "contradictions" not in data:
            data["contradictions"] = []
        if "fraud_risk" not in data:
            data["fraud_risk"] = 0.5
        if "missing_evidence" not in data:
            data["missing_evidence"] = []
        if "reasoning" not in data:
            data["reasoning"] = ""
        if "evidence_gaps" not in data:
            data["evidence_gaps"] = []
        
        # Ensure types are correct
        data["final_confidence"] = float(data.get("final_confidence", 0.5))
        data["fraud_risk"] = float(data.get("fraud_risk", 0.5))
        data["final_confidence"] = max(0.0, min(1.0, data["final_confidence"]))
        data["fraud_risk"] = max(0.0, min(1.0, data["fraud_risk"]))
        
        return data
    
    def _parse_text_response(
        self,
        text: str,
        agent_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse text response when JSON extraction fails."""
        # Fallback to rule-based reasoning
        return self._rule_based_reasoning(
            "unknown",
            Decimal("0"),
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
            diff = abs(float(doc_amount) - float(claim_amount))
            if diff > 100:
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
        
        fraud_confidence = 1.0 - fraud_risk
        confidence_scores.append(fraud_confidence)
        
        if confidence_scores:
            final_confidence = (
                confidence_scores[0] * 0.4 +
                confidence_scores[1] * 0.3 +
                confidence_scores[2] * 0.3
            )
        else:
            final_confidence = 0.5
        
        if contradictions:
            final_confidence *= 0.8
        
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
