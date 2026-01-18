"""
ADK Fraud Agent - Detects fraud patterns using ADK LlmAgent.

Converts the original FraudAgent to use ADK LlmAgent for fraud detection.
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


class ADKFraudAgent:
    """ADK-based agent for fraud detection."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = os.getenv("AGENT_MODEL", "gemini-2.0-flash")
        self.agent = None
        
        if not ADK_AVAILABLE:
            print("⚠️  ADK not available, FraudAgent will use fallback")
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
            
            # Create ADK LlmAgent for fraud detection
            # ADK reads GOOGLE_API_KEY from environment automatically
            self.agent = LlmAgent(
                model=self.model_name,
                name="fraud_agent",
                description="Specialized agent for detecting fraud patterns and risk factors in insurance claims",
                instruction="""You are an insurance claim fraud detection agent. Your job is to detect fraud patterns and risk factors.

**Process:**
1. Analyze claim data and evidence for fraud indicators
2. Extract bill/line item information if available (use document agent results)
3. Compare amounts and check for inconsistencies
4. Identify fraud patterns and risk factors
5. Return structured fraud assessment

**Fraud Indicators to Detect:**
- Amount mismatches: claim_amount vs extracted amounts, document vs image estimates
- Suspicious patterns: timing, frequency, unusual characteristics
- Evidence inconsistencies: contradictions between different evidence sources
- Overpriced items: line items significantly above typical market rates (>20%)
- Invalid/irrelevant items: parts or services not applicable to claim type
- Duplicate charges: same item charged multiple times

**Bill Analysis (if line items available):**
- Extract line items: item name, quantity, unit_price, total
- Compare extracted_total vs claim_amount
- Compare extracted_total vs document agent's extracted amount
- Flag overpriced items (>20% above typical rates)
- Flag invalid/irrelevant items

**Output Format:**
Return JSON with:
- fraud_score: float (0.0-1.0, 0.0 = no fraud, 1.0 = high fraud risk)
- risk_level: string (LOW if < 0.3, MEDIUM if 0.3-0.7, HIGH if > 0.7)
- indicators: array of strings (specific fraud indicators found)
- confidence: float (0.0-1.0)
- notes: string (explanation)
- bill_analysis: object (optional, if line items available) with extracted_total, recommended_amount, line_items, mismatches

Focus on fraud pattern detection. Use document agent results for bill analysis when available.""",
                tools=[],  # Fraud agent focuses on pattern detection, verification handled by orchestrator
            )
        except Exception as e:
            print(f"Failed to initialize ADK FraudAgent: {e}")
            self.agent = None
    
    async def analyze(
        self,
        claim_id: str,
        claim_amount: Decimal,
        claimant_address: str,
        evidence: List[Dict[str, Any]],
        agent_results: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze claim for fraud indicators using ADK agent.
        
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
                "notes": str,
                "check_id": str,
                "bill_analysis": dict (optional, with extracted_total, recommended_amount, line_items, etc.)
            }
        """
        if not self.agent:
            # Fallback to mock analysis
            return self._mock_analysis(claim_id)
        
        # Build context for fraud analysis
        context = self._build_context(
            claim_id, claim_amount, claimant_address, evidence, agent_results
        )
        
        try:
            result = await self._analyze_fraud_with_adk(context, claim_id)
            return result
        except Exception as e:
            print(f"Error in ADK fraud analysis: {e}")
            return {
                "fraud_score": 0.5,
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
    
    async def _analyze_fraud_with_adk(
        self,
        context: str,
        claim_id: str
    ) -> Dict[str, Any]:
        """Analyze fraud using ADK agent."""
        from google.genai import types
        from ..adk_runtime import get_adk_runtime
        
        prompt = f"""Analyze this insurance claim for fraud indicators:

{context}

**Your Tasks:**
1. Check for fraud patterns:
   - Amount mismatches (claim_amount vs evidence amounts)
   - Evidence inconsistencies
   - Suspicious patterns (timing, frequency, unusual characteristics)

2. If bill/line items are available (from document agent):
   - Extract line items: item, quantity, unit_price, total
   - Compare extracted_total vs claim_amount
   - Compare extracted_total vs document agent's extracted amount
   - Flag overpriced items (>20% above typical rates)
   - Flag invalid/irrelevant items

3. Return fraud assessment with indicators and risk level

Return JSON with:
- fraud_score: float (0.0-1.0, 0.0 = no fraud, 1.0 = high fraud risk)
- risk_level: string (LOW if < 0.3, MEDIUM if 0.3-0.7, HIGH if > 0.7)
- indicators: array of strings (specific fraud indicators found)
- confidence: float (0.0-1.0)
- notes: string (explanation)
- bill_analysis: object (optional) with extracted_total, recommended_amount, line_items, mismatches"""
        
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
        session_id = f"fraud_analysis_{claim_id}"
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
            result = self._parse_text_response(response_text)
        
        # Validate against schema
        from ..adk_schemas import validate_against_schema, FRAUD_SCHEMA
        is_valid, validation_errors = validate_against_schema(result, FRAUD_SCHEMA)
        if not is_valid:
            print(f"   └─ ⚠️  Schema validation errors: {', '.join(validation_errors[:3])}")
            # Fix common issues
            result = self._fix_schema_issues(result, validation_errors)
        
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
            "check_id": f"fraud_{claim_id}",
            "bill_analysis": result.get("bill_analysis")  # Include bill analysis if present
        }
    
    def _fix_schema_issues(self, data: Dict[str, Any], errors: List[str]) -> Dict[str, Any]:
        """Fix common schema validation issues."""
        # Ensure required fields exist
        if "fraud_score" not in data:
            data["fraud_score"] = 0.5
        if "risk_level" not in data:
            data["risk_level"] = "MEDIUM"
        if "indicators" not in data:
            data["indicators"] = []
        if "confidence" not in data:
            data["confidence"] = 0.8
        if "notes" not in data:
            data["notes"] = ""
        
        # Ensure types are correct
        data["fraud_score"] = float(data.get("fraud_score", 0.5))
        data["confidence"] = float(data.get("confidence", 0.8))
        data["fraud_score"] = max(0.0, min(1.0, data["fraud_score"]))
        data["confidence"] = max(0.0, min(1.0, data["confidence"]))
        
        return data
    
    def _parse_text_response(self, text: str) -> Dict[str, Any]:
        """Parse text response when JSON extraction fails."""
        fraud_score = 0.1
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
        """Mock analysis when ADK is not available."""
        return {
            "fraud_score": 0.05,
            "risk_level": "LOW",
            "indicators": [],
            "confidence": 0.85,
            "check_id": f"mock_fraud_{claim_id}"
        }
