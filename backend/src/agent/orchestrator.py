"""
Multi-Agent Orchestrator - Coordinates specialized agents for claim evaluation.

Orchestrates parallel agent execution, reasoning, and auto-approval logic.
"""

import os
import asyncio
from typing import Dict, Any, List, Optional
from decimal import Decimal

from ..models import Claim, Evidence
from .agents.document_agent import DocumentAgent
from .agents.image_agent import ImageAgent
from .agents.fraud_agent import FraudAgent
from .agents.reasoning_agent import ReasoningAgent
from ..services.blockchain import get_blockchain_service

try:
    import google.genai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class MultiAgentOrchestrator:
    """Orchestrates multiple specialized agents for claim evaluation."""
    
    def __init__(self):
        # Hackathon Demo: Core 3 agents + reasoning
        self.document_agent = DocumentAgent()
        self.image_agent = ImageAgent()
        self.fraud_agent = FraudAgent()
        self.reasoning_agent = ReasoningAgent()
        self.blockchain = get_blockchain_service()
        
        # Post-Hackathon: Additional agents
        # self.video_agent = VideoAgent()
        # self.audio_agent = AudioAgent()
    
    async def evaluate_claim(
        self,
        claim: Claim,
        evidence: List[Evidence]
    ) -> Dict[str, Any]:
        """
        Orchestrate multi-agent evaluation with auto-approval.
        
        Returns:
            {
                "decision": "AUTO_APPROVED" | "NEEDS_REVIEW",
                "confidence": float,
                "summary": str,  # Comprehensive summary
                "agent_results": {...},
                "reasoning": {...},
                "auto_settled": bool,
                "tx_hash": str | None,
                "review_reasons": List[str] | None
            }
        """
        # Convert Evidence models to dict format
        evidence_dicts = [
            {
                "file_type": e.file_type,
                "file_path": e.file_path
            }
            for e in evidence
        ]
        
        # Run agents in parallel where possible
        agent_results = await self._run_agents_parallel(
            claim.id,
            claim.claim_amount,
            claim.claimant_address,
            evidence_dicts
        )
        
        # Reasoning agent correlates and analyzes
        reasoning_result = await self.reasoning_agent.reason(
            claim.id,
            claim.claim_amount,
            agent_results
        )
        
        # Generate comprehensive summary
        summary = await self._generate_summary(
            claim, agent_results, reasoning_result
        )
        
        # Decision logic
        confidence = reasoning_result["final_confidence"]
        auto_approve = (
            confidence >= 0.95 and
            len(reasoning_result.get("contradictions", [])) == 0 and
            reasoning_result.get("fraud_risk", 1.0) < 0.3
        )
        
        if auto_approve:
            # Auto-approve and settle
            settlement_result = await self._auto_settle(claim, reasoning_result)
            return {
                "decision": "AUTO_APPROVED",
                "confidence": confidence,
                "summary": summary,
                "agent_results": agent_results,
                "reasoning": reasoning_result,
                "auto_settled": True,
                "tx_hash": settlement_result.get("tx_hash"),
                "review_reasons": None
            }
        
        # Send to manual review
        return {
            "decision": "NEEDS_REVIEW",
            "confidence": confidence,
            "summary": summary,
            "agent_results": agent_results,
            "reasoning": reasoning_result,
            "auto_settled": False,
            "tx_hash": None,
            "review_reasons": self._get_review_reasons(reasoning_result)
        }
    
    async def _run_agents_parallel(
        self,
        claim_id: str,
        claim_amount: Decimal,
        claimant_address: str,
        evidence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Run specialized agents in parallel."""
        tasks = []
        
        # Find evidence by type (Hackathon: document and image only)
        documents = [e for e in evidence if e.get("file_type") == "document"]
        images = [e for e in evidence if e.get("file_type") == "image"]
        
        # Run agents in parallel (Hackathon: 3 agents)
        agent_results = {}
        
        # Create tasks
        if documents:
            tasks.append(("document", self.document_agent.analyze(claim_id, documents)))
        if images:
            tasks.append(("image", self.image_agent.analyze(claim_id, images)))
        
        # Always run fraud agent (needs all evidence and other agent results)
        # We'll run it after document/image agents complete
        if tasks:
            # Wait for document/image agents
            results = await asyncio.gather(*[task[1] for task in tasks])
            
            # Build results dict
            for i, (agent_type, _) in enumerate(tasks):
                agent_results[agent_type] = results[i]
        
        # Now run fraud agent with access to other results
        fraud_result = await self.fraud_agent.analyze(
            claim_id,
            claim_amount,
            claimant_address,
            evidence,
            agent_results
        )
        agent_results["fraud"] = fraud_result
        
        return agent_results
    
    async def _generate_summary(
        self,
        claim: Claim,
        agent_results: Dict[str, Any],
        reasoning_result: Dict[str, Any]
    ) -> str:
        """Generate comprehensive summary for auto-approval."""
        if not GEMINI_AVAILABLE or not genai:
            # Fallback to template-based summary
            return self._generate_template_summary(claim, agent_results, reasoning_result)
        
        try:
            api_key = os.getenv("GOOGLE_AI_API_KEY")
            if not api_key:
                return self._generate_template_summary(claim, agent_results, reasoning_result)
            
            client = genai.Client(api_key=api_key)
            model_name = "gemini-2.0-flash"
            
            prompt = f"""Generate a comprehensive summary for this insurance claim evaluation:

Claim ID: {claim.id}
Claim Amount: ${float(claim.claim_amount):,.2f}
Claimant: {claim.claimant_address}

Agent Analysis Results:
{self._format_agent_results(agent_results)}

Reasoning:
- Confidence: {reasoning_result.get('final_confidence', 0):.2%}
- Contradictions: {len(reasoning_result.get('contradictions', []))}
- Fraud Risk: {reasoning_result.get('fraud_risk', 0):.2f}

Provide a clear, professional summary suitable for automatic approval or manual review.
Include key findings from each agent and the overall assessment."""
            
            # Use new API with async client
            aio_client = client.aio
            
            # Use async API
            response = await aio_client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            
            # Parse response
            if hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'candidates') and response.candidates:
                return response.candidates[0].content.parts[0].text
            else:
                return str(response)
        except Exception as e:
            print(f"Error generating AI summary: {e}")
            return self._generate_template_summary(claim, agent_results, reasoning_result)
    
    def _generate_template_summary(
        self,
        claim: Claim,
        agent_results: Dict[str, Any],
        reasoning_result: Dict[str, Any]
    ) -> str:
        """Generate template-based summary when AI is not available."""
        summary_parts = [
            f"Claim Evaluation Summary for Claim {claim.id}",
            f"Claim Amount: ${float(claim.claim_amount):,.2f}",
            "",
            "Agent Analysis:"
        ]
        
        if "document" in agent_results:
            doc_result = agent_results["document"]
            summary_parts.append(f"- Document: {'Valid' if doc_result.get('valid') else 'Invalid'}")
            if doc_result.get("extracted_data"):
                data = doc_result["extracted_data"]
                summary_parts.append(f"  Amount: ${data.get('amount', 0):,.2f}")
        
        if "image" in agent_results:
            img_result = agent_results["image"]
            summary_parts.append(f"- Image: {'Valid' if img_result.get('valid') else 'Invalid'}")
            if img_result.get("damage_assessment"):
                assessment = img_result["damage_assessment"]
                summary_parts.append(f"  Damage: {assessment.get('damage_type', 'unknown')}")
        
        if "fraud" in agent_results:
            fraud_result = agent_results["fraud"]
            summary_parts.append(f"- Fraud Risk: {fraud_result.get('risk_level', 'UNKNOWN')}")
        
        summary_parts.append("")
        summary_parts.append(f"Overall Confidence: {reasoning_result.get('final_confidence', 0):.2%}")
        summary_parts.append(f"Decision: {reasoning_result.get('reasoning', 'Pending review')}")
        
        return "\n".join(summary_parts)
    
    async def _auto_settle(
        self,
        claim: Claim,
        reasoning_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Automatically settle approved claim."""
        try:
            tx_hash = await self.blockchain.approve_claim(
                claim_id=claim.id,
                amount=claim.claim_amount,
                recipient=claim.claimant_address
            )
            return {"tx_hash": tx_hash}
        except Exception as e:
            print(f"Error in auto-settlement: {e}")
            return {"tx_hash": None, "error": str(e)}
    
    def _get_review_reasons(self, reasoning_result: Dict[str, Any]) -> List[str]:
        """Extract reasons why claim needs manual review."""
        reasons = []
        confidence = reasoning_result.get("final_confidence", 0)
        if confidence < 0.95:
            reasons.append(f"Confidence {confidence:.2%} below 95% threshold")
        
        contradictions = reasoning_result.get("contradictions", [])
        if contradictions:
            reasons.append(f"{len(contradictions)} contradiction(s) detected")
        
        fraud_risk = reasoning_result.get("fraud_risk", 0)
        if fraud_risk >= 0.3:
            reasons.append(f"High fraud risk: {fraud_risk:.2f}")
        
        missing_evidence = reasoning_result.get("missing_evidence", [])
        if missing_evidence:
            reasons.append(f"Missing evidence: {', '.join(missing_evidence)}")
        
        return reasons
    
    def _format_agent_results(self, agent_results: Dict[str, Any]) -> str:
        """Format agent results for summary generation."""
        formatted = []
        for agent_type, result in agent_results.items():
            if result:
                summary = result.get("summary", "Analysis completed")
                formatted.append(f"{agent_type.upper()}: {summary}")
        return "\n".join(formatted)


# Singleton instance
_orchestrator: Optional[MultiAgentOrchestrator] = None


def get_orchestrator() -> MultiAgentOrchestrator:
    """Get or create the orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiAgentOrchestrator()
    return _orchestrator
