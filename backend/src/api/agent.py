"""
Agent API endpoint.
POST /agent/evaluate/{claimId} - Trigger AI agent evaluation

Uses Google Agents Framework with Gemini for claim evaluation.
"""

import uuid
import os
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Claim, Evidence, Evaluation, AgentResult, AgentLog, UserWallet
from ..agent.adk_agents.orchestrator import get_adk_orchestrator
from ..agent.tools import set_wallet_address
from ..api.auth import get_current_user

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


class AgentLogResponse(BaseModel):
    """Response model for agent log entry."""
    id: str
    claim_id: str
    agent_type: str
    message: str
    log_level: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: str


class AgentLogsResponse(BaseModel):
    """Response model for agent logs list."""
    claim_id: str
    logs: List[AgentLogResponse]


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
    decision: str  # AUTO_APPROVED, APPROVED_WITH_REVIEW, NEEDS_REVIEW, NEEDS_MORE_DATA, INSUFFICIENT_DATA, FRAUD_DETECTED, REJECTED
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


class ChatRequest(BaseModel):
    message: str
    role: Optional[str] = None  # claimant|insurer
    claim_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str


@router.post("/evaluate/{claim_id}", response_model=EvaluationResponse)
async def evaluate_claim(
    claim_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Trigger AI agent evaluation of a claim.
    
    The agent will:
    1. Call verify_document (x402 payment: $0.05)
    2. Call verify_image (x402 payment: $0.10)
    3. Call verify_fraud (x402 payment: $0.05)
    4. Make decision based on results
    
    Total cost: ~$0.20 USDC per evaluation (paid by insurer wallet)
    
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
    
    # Log evaluation start
    log_agent_activity(
        db, claim_id, "orchestrator",
        f"Starting evaluation for claim {claim_id} (Amount: ${float(claim.claim_amount):,.2f})",
        "INFO", {"claim_amount": float(claim.claim_amount), "claimant": claim.claimant_address}
    )
    
    # Get evidence
    evidence = db.query(Evidence).filter(Evidence.claim_id == claim_id).all()
    
    if evidence:
        log_agent_activity(
            db, claim_id, "orchestrator",
            f"Found {len(evidence)} evidence file(s) to analyze",
            "INFO", {"evidence_count": len(evidence), "file_types": [e.file_type for e in evidence]}
        )
    else:
        log_agent_activity(
            db, claim_id, "orchestrator",
            "No evidence files found - will request additional data",
            "WARNING"
        )
    
    # Set wallet address in context for x402 payments
    # Use insurer's wallet address from UserWallet table for agent payments
    wallet_address = None
    if current_user:
        # Get wallet address from UserWallet table
        user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
        wallet_address = user_wallet.wallet_address if user_wallet else None
        
        if wallet_address:
            set_wallet_address(wallet_address)
            log_agent_activity(
                db, claim_id, "orchestrator",
                f"Using insurer wallet for x402 payments: {wallet_address[:10]}...",
                "INFO", {"wallet_address": wallet_address[:10] + "..."}
            )
        else:
            log_agent_activity(
                db, claim_id, "orchestrator",
                "Warning: Insurer wallet address not found, x402 payments may fail",
                "WARNING"
            )
    else:
        log_agent_activity(
            db, claim_id, "orchestrator",
            "Warning: Current user not available, x402 payments may fail",
            "WARNING"
        )
    
    # Run multi-agent evaluation using ADK orchestrator
    # Pass db session so orchestrator can log activities
    orchestrator = get_adk_orchestrator()
    evaluation_result = await orchestrator.evaluate_claim(claim, evidence, db=db)
    
    # Get agent results from evaluation
    # The orchestrator agent returns tool_results (keyed by tool name like "verify_document")
    # while manual coordination returns agent_results (keyed by agent type like "document")
    raw_agent_results = evaluation_result.get("agent_results", {})
    
    # Check if we have tool_results format (from orchestrator agent)
    # The orchestrator agent sets agent_results = tool_results, so keys are tool names
    # We need to detect if keys are tool names (like "verify_document") vs agent types (like "document")
    tool_name_keys = {"verify_document", "verify_image", "verify_fraud", "approve_claim"}
    has_tool_name_keys = raw_agent_results and any(key in tool_name_keys for key in raw_agent_results.keys())
    
    if has_tool_name_keys:
        # Convert tool_results to agent_results format
        log_agent_activity(
            db, claim_id, "orchestrator",
            "Converting tool_results to agent_results format for database storage",
            "INFO", {"tool_count": len(raw_agent_results), "tool_names": list(raw_agent_results.keys())}
        )
        raw_agent_results = _convert_tool_results_to_agent_results(raw_agent_results)
        log_agent_activity(
            db, claim_id, "orchestrator",
            f"Converted {len(raw_agent_results)} tool result(s) to agent results",
            "INFO", {"agent_types": list(raw_agent_results.keys())}
        )
    elif not raw_agent_results and evaluation_result.get("tool_results"):
        # Fallback: if agent_results is empty but tool_results exists, use it
        log_agent_activity(
            db, claim_id, "orchestrator",
            "Converting tool_results to agent_results format for database storage (fallback)",
            "INFO", {"tool_count": len(evaluation_result.get("tool_results", {}))}
        )
        raw_agent_results = _convert_tool_results_to_agent_results(
            evaluation_result.get("tool_results", {})
        )
        log_agent_activity(
            db, claim_id, "orchestrator",
            f"Converted {len(raw_agent_results)} tool result(s) to agent results",
            "INFO", {"agent_types": list(raw_agent_results.keys())}
        )
    
    # Store agent results in database incrementally
    # This allows the status endpoint to show progress
    agent_results_dict = {}
    for agent_type, agent_result in raw_agent_results.items():
        agent_result_record = AgentResult(
            id=str(uuid.uuid4()),
            claim_id=claim_id,
            agent_type=agent_type,
            result=agent_result,
            confidence=agent_result.get("confidence"),
            created_at=datetime.utcnow()
        )
        db.add(agent_result_record)
        db.commit()  # Commit each result so status endpoint can see progress
        agent_results_dict[agent_type] = {
            "result": agent_result,
            "confidence": agent_result.get("confidence"),
            "created_at": agent_result_record.created_at.isoformat() if agent_result_record.created_at else None
        }
        log_agent_activity(
            db, claim_id, "orchestrator",
            f"Stored {agent_type} agent result in database",
            "INFO", {"agent_type": agent_type, "has_confidence": agent_result.get("confidence") is not None}
        )
    
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
    elif decision == "FRAUD_DETECTED":
        claim.status = "REJECTED"  # Fraud detected - immediate rejection
        claim.approved_amount = None
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
    
    # Use agent_results_dict we built during evaluation
    # (already populated above, no need to query again)
    
    # Build tool calls list and calculate actual costs based on what agents ran
    tool_calls_list = []
    total_processing_cost = Decimal("0.00")
    
    # Tool costs (in USDC) - reduced costs
    TOOL_COSTS = {
        "verify_document": Decimal("0.05"),
        "verify_image": Decimal("0.10"),
        "verify_fraud": Decimal("0.05"),
    }
    
    # Extract tool calls from evaluation result if available
    if "tool_calls" in evaluation_result:
        for tool_call in evaluation_result["tool_calls"]:
            tool_name = tool_call.get("tool_name", "")
            cost = tool_call.get("cost")
            if cost is not None:
                total_processing_cost += Decimal(str(cost))
            
            tool_calls_list.append(ToolCall(
                tool_name=tool_name,
                status=tool_call.get("status", "completed"),
                cost=cost,
                timestamp=tool_call.get("timestamp")
            ))
    else:
        # Fallback: infer tool calls from agent results (dynamic based on what ran)
        if "document" in agent_results_dict:
            cost = float(TOOL_COSTS["verify_document"])
            total_processing_cost += TOOL_COSTS["verify_document"]
            tool_calls_list.append(ToolCall(
                tool_name="verify_document",
                status="completed",
                cost=cost,
                timestamp=None
            ))
        
        if "image" in agent_results_dict:
            cost = float(TOOL_COSTS["verify_image"])
            total_processing_cost += TOOL_COSTS["verify_image"]
            tool_calls_list.append(ToolCall(
                tool_name="verify_image",
                status="completed",
                cost=cost,
                timestamp=None
            ))
        
        # Fraud agent always runs (doesn't depend on evidence type)
        if "fraud" in agent_results_dict:
            cost = float(TOOL_COSTS["verify_fraud"])
            total_processing_cost += TOOL_COSTS["verify_fraud"]
            tool_calls_list.append(ToolCall(
                tool_name="verify_fraud",
                status="completed",
                cost=cost,
                timestamp=None
            ))
        
        # Settlement is not a cost
        if claim.auto_settled and claim.tx_hash:
            tool_calls_list.append(ToolCall(
                tool_name="approve_claim",
                status="completed",
                cost=None,  # Settlement, not a cost
                timestamp=None
            ))
    
    # Update claim with actual processing costs
    claim.processing_costs = total_processing_cost
    db.commit()
    
    return EvaluationResponse(
        claim_id=str(claim_id),
        decision=decision,
        confidence=evaluation_result["confidence"],
        approved_amount=float(claim.approved_amount) if claim.approved_amount else None,
        reasoning=reasoning_text or evaluation_result.get("summary", ""),
        processing_costs=float(total_processing_cost),  # Dynamic cost based on actual usage
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
    
    # Get evidence to determine which agents should run
    evidence = db.query(Evidence).filter(Evidence.claim_id == claim_id).all()
    has_documents = any(e.file_type == "document" for e in evidence)
    has_images = any(e.file_type == "image" for e in evidence)
    
    # Expected agents based on evidence (fraud always runs, reasoning always runs)
    expected_agents = []
    if has_documents:
        expected_agents.append("document")
    if has_images:
        expected_agents.append("image")
    expected_agents.append("fraud")  # Always runs
    expected_agents.append("reasoning")  # Always runs
    
    pending_agents = [agent for agent in expected_agents if agent not in completed_agents]
    
    # Calculate progress based on actual expected agents
    progress_percentage = (len(completed_agents) / len(expected_agents)) * 100.0 if expected_agents else 0.0
    
    return EvaluationStatusResponse(
        claim_id=str(claim_id),
        status=claim.status,
        completed_agents=completed_agents,
        pending_agents=pending_agents,
        progress_percentage=progress_percentage
    )


@router.get("/logs/{claim_id}", response_model=AgentLogsResponse)
async def get_agent_logs(
    claim_id: str,
    db: Session = Depends(get_db)
):
    """
    Get agent activity logs for a claim.
    
    Returns real-time logs showing what agents are doing/reasoning during evaluation.
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
    
    # Get agent logs, ordered by creation time
    logs = db.query(AgentLog).filter(
        AgentLog.claim_id == claim_id
    ).order_by(AgentLog.created_at.asc()).all()
    
    # Convert to response format
    logs_list = [
        AgentLogResponse(
            id=str(log.id),
            claim_id=str(log.claim_id),
            agent_type=log.agent_type,
            message=log.message,
            log_level=log.log_level,
            metadata=log.log_metadata,  # Use log_metadata instead of metadata
            created_at=log.created_at.isoformat() if log.created_at else ""
        )
        for log in logs
    ]
    
    return AgentLogsResponse(
        claim_id=str(claim_id),
        logs=logs_list
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_assistant(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """
    Lightweight AI chat assistant endpoint.

    - If GOOGLE_AI_API_KEY/GOOGLE_API_KEY is configured, uses Gemini to answer.
    - Otherwise returns a deterministic, helpful fallback response (demo-friendly).
    """
    role = (request.role or "user").strip()
    message = (request.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    claim_context = None
    if request.claim_id:
        claim = db.query(Claim).filter(Claim.id == request.claim_id).first()
        if claim:
            claim_context = {
                "id": claim.id,
                "status": claim.status,
                "decision": claim.decision,
                "confidence": float(claim.confidence) if claim.confidence else None,
                "approved_amount": float(claim.approved_amount) if claim.approved_amount else None,
                "requested_data": claim.requested_data,
                "description": getattr(claim, "description", None),
            }

    api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        if claim_context:
            reply = (
                f"Claim {claim_context['id'][:8]} is currently {claim_context['status']}. "
                "If it needs info, upload the requested evidence; if it’s approved, you can settle it."
            )
        else:
            reply = (
                "I can help: submit a claim → evaluation runs → you may be asked for more evidence → "
                "insurer reviews and settles approved claims."
            )
        return ChatResponse(reply=reply)

    try:
        import google.genai as genai

        client = genai.Client(api_key=api_key)
        model_name = os.getenv("AGENT_MODEL", "gemini-2.0-flash")

        context_block = ""
        if claim_context:
            context_block = f"\n\nClaim context (authoritative):\n{claim_context}\n"

        system = (
            "You are UClaim's in-product assistant. "
            "Be concise, accurate, and role-aware. "
            "Avoid crypto jargon; say 'enable settlements' instead of 'connect wallet'. "
            "Never claim you moved funds. "
            "If you are unsure, ask the user what they see on screen."
        )

        prompt = f"{system}\n\nRole: {role}\nUser message: {message}{context_block}"

        aio_client = client.aio
        response = await aio_client.models.generate_content(
            model=model_name,
            contents=prompt,
        )

        text = getattr(response, "text", None)
        if text:
            return ChatResponse(reply=text.strip())
        if getattr(response, "candidates", None):
            cand = response.candidates[0]
            return ChatResponse(reply=cand.content.parts[0].text.strip())
        return ChatResponse(reply=str(response))
    except Exception as e:
        return ChatResponse(reply=f"I couldn't reach the AI model right now. ({type(e).__name__})")


def _convert_tool_results_to_agent_results(tool_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert tool_results (keyed by tool name) to agent_results (keyed by agent type).
    
    The orchestrator agent returns tool_results with keys like "verify_document",
    but we need agent_results with keys like "document" to store in the database.
    """
    agent_results = {}
    
    # Map tool names to agent types
    tool_to_agent = {
        "verify_document": "document",
        "verify_image": "image",
        "verify_fraud": "fraud"
    }
    
    for tool_name, tool_result in tool_results.items():
        agent_type = tool_to_agent.get(tool_name)
        if agent_type:
            agent_results[agent_type] = tool_result
    
    return agent_results


def log_agent_activity(
    db: Session,
    claim_id: str,
    agent_type: str,
    message: str,
    log_level: str = "INFO",
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Helper function to log agent activity.
    
    This should be called throughout the agent evaluation process to track what's happening.
    """
    try:
        log_entry = AgentLog(
            id=str(uuid.uuid4()),
            claim_id=claim_id,
            agent_type=agent_type,
            message=message,
            log_level=log_level,
            log_metadata=metadata or {},  # Use log_metadata instead of metadata
            created_at=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        # Don't fail evaluation if logging fails
        print(f"Error logging agent activity: {e}")


# Using ADK Orchestrator for claim evaluation
