"""
Agent API endpoint.
POST /agent/evaluate/{claimId} - Trigger AI agent evaluation

Uses Google Agents Framework with Gemini for claim evaluation.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Claim, Evidence, Evaluation, AgentResult
from ..agent.adk_agents.orchestrator import get_adk_orchestrator

router = APIRouter(prefix="/agent", tags=["agent"])


class ToolCall(BaseModel):
    """Model for tool call information."""
    tool_name: str  # verify_document, verify_image, verify_fraud, approve_claim
    status: str  # pending, completed, failed
    cost: Optional[float] = None  # USDC amount
    timestamp: Optional[str] = None


class AgentResultResponse(BaseModel):
    """Response model for individual agent result."""
    agent_type: str
    result: Dict[str, Any]
    confidence: Optional[float] = None
    created_at: str


class AgentResultsResponse(BaseModel):
    """Response model for agent results list."""
    claim_id: str
    agent_results: List[AgentResultResponse]


class EvaluationStatusResponse(BaseModel):
    """Response model for evaluation status."""
    claim_id: str
    status: str  # EVALUATING, APPROVED, etc.
    completed_agents: List[str]  # List of agent types that have completed
    pending_agents: List[str]  # List of agent types still pending
    progress_percentage: float  # 0.0 to 100.0


class EvaluationResponse(BaseModel):
    """Response model for agent evaluation."""
    claim_id: str
    decision: str  # AUTO_APPROVED, APPROVED_WITH_REVIEW, NEEDS_REVIEW, NEEDS_MORE_DATA, INSUFFICIENT_DATA, REJECTED
    confidence: float
    approved_amount: Optional[float] = None
    reasoning: str
    processing_costs: float
    summary: Optional[str] = None  # Comprehensive summary
    auto_approved: bool = False
    auto_settled: bool = False
    tx_hash: Optional[str] = None
    review_reasons: Optional[list] = None
    requested_data: Optional[list] = None  # Types of additional data requested
    human_review_required: Optional[bool] = False  # Human-in-the-loop flag
    agent_results: Optional[Dict[str, Any]] = None  # Structured agent results
    tool_calls: Optional[List[ToolCall]] = None  # List of tools called during evaluation


class EvaluationRequest(BaseModel):
    """Request model for evaluation trigger."""
    # Optional parameters for evaluation
    pass


@router.post("/evaluate/{claim_id}", response_model=EvaluationResponse)
async def evaluate_claim(
    claim_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger AI agent evaluation of a claim.
    
    The agent will:
    1. Call verify_document (x402 payment: $0.10)
    2. Call verify_image (x402 payment: $0.15)
    3. Call verify_fraud (x402 payment: $0.10)
    4. Make decision based on results
    
    Decision rules:
    - confidence >= 0.85 → APPROVED
    - confidence < 0.85 → NEEDS_REVIEW
    
    **Fail-closed:** No funds move unless confidence >= 0.85
    """
    # Validate UUID format
    try:
        uuid.UUID(claim_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid claim ID format")
    
    # Get claim (using string ID)
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    if claim.status not in ["SUBMITTED", "NEEDS_REVIEW"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Claim cannot be evaluated. Current status: {claim.status}"
        )
    
    # Update status to EVALUATING
    claim.status = "EVALUATING"
    db.commit()
    
    # Get evidence
    evidence = db.query(Evidence).filter(Evidence.claim_id == claim_id).all()
    
    # Run multi-agent evaluation using ADK orchestrator
    orchestrator = get_adk_orchestrator()
    evaluation_result = await orchestrator.evaluate_claim(claim, evidence)
    
    # Store agent results in database
    for agent_type, agent_result in evaluation_result.get("agent_results", {}).items():
        agent_result_record = AgentResult(
            id=str(uuid.uuid4()),
            claim_id=claim_id,
            agent_type=agent_type,
            result=agent_result,
            confidence=agent_result.get("confidence"),
            created_at=datetime.utcnow()
        )
        db.add(agent_result_record)
    
    # Update claim with results
    decision = evaluation_result["decision"]
    claim.decision = decision
    claim.confidence = Decimal(str(evaluation_result["confidence"]))
    claim.comprehensive_summary = evaluation_result.get("summary")
    claim.auto_approved = (decision == "AUTO_APPROVED")
    claim.auto_settled = evaluation_result.get("auto_settled", False)
    claim.review_reasons = evaluation_result.get("review_reasons")
    claim.requested_data = evaluation_result.get("requested_data", [])
    claim.human_review_required = evaluation_result.get("human_review_required", False)
    
    # Update status based on decision
    if decision == "AUTO_APPROVED":
        claim.status = "APPROVED"
        claim.approved_amount = claim.claim_amount
        if evaluation_result.get("tx_hash"):
            claim.tx_hash = evaluation_result["tx_hash"]
            claim.status = "SETTLED"
    elif decision in ["NEEDS_MORE_DATA", "INSUFFICIENT_DATA"]:
        claim.status = "AWAITING_DATA"
        claim.approved_amount = None
    elif decision == "APPROVED_WITH_REVIEW":
        claim.status = "APPROVED"  # Approved but needs human confirmation before settlement
        claim.approved_amount = claim.claim_amount
    else:  # NEEDS_REVIEW or other
        claim.status = "NEEDS_REVIEW"
        claim.approved_amount = None
    
    # Store evaluation reasoning
    reasoning_text = evaluation_result.get("reasoning", {})
    if isinstance(reasoning_text, dict):
        reasoning_text = reasoning_text.get("reasoning", str(reasoning_text))
    
    evaluation = Evaluation(
        id=str(uuid.uuid4()),
        claim_id=claim_id,
        reasoning=reasoning_text or evaluation_result.get("summary", ""),
        created_at=datetime.utcnow()
    )
    db.add(evaluation)
    db.commit()
    
    # Build agent results dict from stored results
    agent_results_dict = {}
    stored_results = db.query(AgentResult).filter(AgentResult.claim_id == claim_id).all()
    for stored_result in stored_results:
        agent_results_dict[stored_result.agent_type] = {
            "result": stored_result.result,
            "confidence": stored_result.confidence,
            "created_at": stored_result.created_at.isoformat() if stored_result.created_at else None
        }
    
    # Build tool calls list (extract from agent results or orchestrator)
    tool_calls_list = []
    # Extract tool calls from evaluation result if available
    if "tool_calls" in evaluation_result:
        for tool_call in evaluation_result["tool_calls"]:
            tool_calls_list.append(ToolCall(
                tool_name=tool_call.get("tool_name", ""),
                status=tool_call.get("status", "completed"),
                cost=tool_call.get("cost"),
                timestamp=tool_call.get("timestamp")
            ))
    else:
        # Fallback: infer tool calls from agent results
        if "document" in agent_results_dict:
            tool_calls_list.append(ToolCall(
                tool_name="verify_document",
                status="completed",
                cost=0.10,
                timestamp=None
            ))
        if "image" in agent_results_dict:
            tool_calls_list.append(ToolCall(
                tool_name="verify_image",
                status="completed",
                cost=0.15,
                timestamp=None
            ))
        if "fraud" in agent_results_dict:
            tool_calls_list.append(ToolCall(
                tool_name="verify_fraud",
                status="completed",
                cost=0.10,
                timestamp=None
            ))
        if claim.auto_settled and claim.tx_hash:
            tool_calls_list.append(ToolCall(
                tool_name="approve_claim",
                status="completed",
                cost=None,  # Settlement, not a cost
                timestamp=None
            ))
    
    return EvaluationResponse(
        claim_id=str(claim_id),
        decision=decision,
        confidence=evaluation_result["confidence"],
        approved_amount=float(claim.approved_amount) if claim.approved_amount else None,
        reasoning=reasoning_text or evaluation_result.get("summary", ""),
        processing_costs=0.35,  # Total x402 costs
        summary=evaluation_result.get("summary"),
        auto_approved=claim.auto_approved,
        auto_settled=claim.auto_settled,
        tx_hash=evaluation_result.get("tx_hash"),
        review_reasons=evaluation_result.get("review_reasons"),
        requested_data=evaluation_result.get("requested_data", []),
        human_review_required=evaluation_result.get("human_review_required", False),
        agent_results=agent_results_dict,
        tool_calls=tool_calls_list if tool_calls_list else None
    )


@router.get("/results/{claim_id}", response_model=AgentResultsResponse)
async def get_agent_results(
    claim_id: str,
    db: Session = Depends(get_db)
):
    """
    Get agent results for a claim.
    
    Returns all agent results stored for the claim, including:
    - Document agent results
    - Image agent results
    - Fraud agent results
    - Reasoning agent results
    """
    # Validate UUID format
    try:
        uuid.UUID(claim_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid claim ID format")
    
    # Verify claim exists
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Get agent results
    agent_results = db.query(AgentResult).filter(AgentResult.claim_id == claim_id).all()
    
    # Convert to response format
    agent_results_list = [
        AgentResultResponse(
            agent_type=result.agent_type,
            result=result.result,
            confidence=result.confidence,
            created_at=result.created_at.isoformat() if result.created_at else ""
        )
        for result in agent_results
    ]
    
    return AgentResultsResponse(
        claim_id=str(claim_id),
        agent_results=agent_results_list
    )


@router.get("/status/{claim_id}", response_model=EvaluationStatusResponse)
async def get_evaluation_status(
    claim_id: str,
    db: Session = Depends(get_db)
):
    """
    Get real-time evaluation status for a claim.
    
    Returns:
    - Current status
    - Which agents have completed
    - Which agents are pending
    - Progress percentage
    """
    # Validate UUID format
    try:
        uuid.UUID(claim_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid claim ID format")
    
    # Get claim
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Get agent results to determine which agents have completed
    agent_results = db.query(AgentResult).filter(AgentResult.claim_id == claim_id).all()
    completed_agents = [result.agent_type for result in agent_results]
    
    # Expected agents
    expected_agents = ["document", "image", "fraud", "reasoning"]
    pending_agents = [agent for agent in expected_agents if agent not in completed_agents]
    
    # Calculate progress
    progress_percentage = (len(completed_agents) / len(expected_agents)) * 100.0 if expected_agents else 0.0
    
    return EvaluationStatusResponse(
        claim_id=str(claim_id),
        status=claim.status,
        completed_agents=completed_agents,
        pending_agents=pending_agents,
        progress_percentage=progress_percentage
    )


# Using ADK Orchestrator for claim evaluation
