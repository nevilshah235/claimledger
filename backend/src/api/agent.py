"""
Agent API endpoint.
POST /agent/evaluate/{claimId} - Trigger AI agent evaluation

Uses Google Agents Framework with Gemini for claim evaluation.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Claim, Evidence, Evaluation

router = APIRouter(prefix="/agent", tags=["agent"])


class EvaluationResponse(BaseModel):
    """Response model for agent evaluation."""
    claim_id: str
    decision: str  # APPROVED, NEEDS_REVIEW, REJECTED
    confidence: float
    approved_amount: Optional[float] = None
    reasoning: str
    processing_costs: float


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
    
    # Run agent evaluation
    # TODO: Integrate Google Agents Framework
    # For now, use mock evaluation for demo
    evaluation_result = await run_mock_evaluation(claim, evidence, db)
    
    # Update claim with results
    claim.decision = evaluation_result["decision"]
    claim.confidence = Decimal(str(evaluation_result["confidence"]))
    claim.processing_costs = Decimal(str(evaluation_result["processing_costs"]))
    
    if evaluation_result["decision"] == "APPROVED":
        claim.status = "APPROVED"
        claim.approved_amount = claim.claim_amount  # Full amount for demo
    else:
        claim.status = "NEEDS_REVIEW"
        claim.approved_amount = None
    
    # Store evaluation reasoning
    evaluation = Evaluation(
        id=str(uuid.uuid4()),
        claim_id=claim_id,
        reasoning=evaluation_result["reasoning"],
        created_at=datetime.utcnow()
    )
    db.add(evaluation)
    db.commit()
    
    return EvaluationResponse(
        claim_id=str(claim_id),
        decision=evaluation_result["decision"],
        confidence=evaluation_result["confidence"],
        approved_amount=float(claim.approved_amount) if claim.approved_amount else None,
        reasoning=evaluation_result["reasoning"],
        processing_costs=evaluation_result["processing_costs"]
    )


async def run_mock_evaluation(claim, evidence, db) -> dict:
    """
    Mock evaluation for demo purposes.
    
    In production, this would:
    1. Initialize Google Agents Framework agent
    2. Call verify_document, verify_image, verify_fraud tools
    3. Each tool call triggers x402 payment
    4. Return structured decision
    """
    # Simulate x402 payments
    # Document: $0.10, Image: $0.15, Fraud: $0.10
    total_costs = 0.35
    
    # Mock high confidence for demo happy path
    confidence = 0.92
    decision = "APPROVED" if confidence >= 0.85 else "NEEDS_REVIEW"
    
    reasoning = (
        f"Document verified: ${float(claim.claim_amount):,.2f} repair invoice from Auto Repair Shop. "
        f"Image analysis shows front bumper damage consistent with invoice description. "
        f"Fraud score: 0.05 (low risk). "
        f"Confidence: {confidence * 100:.0f}%. "
        f"Recommendation: {decision}"
    )
    
    return {
        "decision": decision,
        "confidence": confidence,
        "approved_amount": float(claim.claim_amount) if decision == "APPROVED" else None,
        "reasoning": reasoning,
        "processing_costs": total_costs
    }
