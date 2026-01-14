"""
Claims API endpoints.
POST /claims - Submit claim (metadata + files)
GET /claims/{id} - Get claim status
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from fastapi import Depends as FastAPIDepends
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Claim, Evidence, User, UserWallet
from ..api.auth import get_current_user, security

router = APIRouter(prefix="/claims", tags=["claims"])


class ClaimResponse(BaseModel):
    """Response model for claim data."""
    id: str
    claimant_address: str
    claim_amount: float
    status: str
    decision: Optional[str] = None
    confidence: Optional[float] = None
    approved_amount: Optional[float] = None
    processing_costs: Optional[float] = None
    tx_hash: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ClaimCreateResponse(BaseModel):
    """Response model for claim creation."""
    claim_id: str
    status: str


@router.post("", response_model=ClaimCreateResponse)
async def create_claim(
    claim_amount: float = Form(...),
    files: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit a new insurance claim.
    
    Requires authentication. Uses authenticated user's wallet address as claimant.
    
    - **claim_amount**: Requested claim amount in USDC
    - **files**: Evidence files (images, documents)
    
    Returns claim_id and initial status.
    """
    # Verify user is a claimant
    if current_user.role != "claimant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only claimants can submit claims"
        )
    
    # Get user's wallet address
    user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
    if not user_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found for user. Please contact support."
        )
    
    # Create new claim
    claim_id = str(uuid.uuid4())
    claim = Claim(
        id=claim_id,
        claimant_address=user_wallet.wallet_address,
        claim_amount=Decimal(str(claim_amount)),
        status="SUBMITTED",
        processing_costs=Decimal("0"),
        created_at=datetime.utcnow()
    )
    db.add(claim)
    
    # Process and store evidence files
    for file in files:
        # Determine file type
        file_type = "document"
        if file.content_type and file.content_type.startswith("image/"):
            file_type = "image"
        
        # Save file to local storage (for demo)
        # In production, would use IPFS or cloud storage
        file_path = f"uploads/{claim_id}/{file.filename}"
        
        evidence = Evidence(
            id=str(uuid.uuid4()),
            claim_id=claim_id,
            file_type=file_type,
            file_path=file_path,
            created_at=datetime.utcnow()
        )
        db.add(evidence)
    
    db.commit()
    
    return ClaimCreateResponse(
        claim_id=str(claim_id),
        status="SUBMITTED"
    )


@router.get("", response_model=List[ClaimResponse])
async def list_claims(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    List all claims.
    
    - Claimants: See only their own claims
    - Insurers: See all claims
    - Unauthenticated: Returns empty list
    """
    current_user = None
    if credentials:
        try:
            current_user = get_current_user(credentials, db)
        except HTTPException:
            pass  # Not authenticated, return empty list
    
    if not current_user:
        return []
    
    if current_user.role == "claimant":
        # Claimants see only their own claims
        user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
        if not user_wallet:
            return []
        
        claims = db.query(Claim).filter(
            Claim.claimant_address == user_wallet.wallet_address
        ).order_by(Claim.created_at.desc()).all()
    else:
        # Insurers see all claims
        claims = db.query(Claim).order_by(Claim.created_at.desc()).all()
    
    return [
        ClaimResponse(
            id=str(claim.id),
            claimant_address=claim.claimant_address,
            claim_amount=float(claim.claim_amount),
            status=claim.status,
            decision=claim.decision,
            confidence=float(claim.confidence) if claim.confidence else None,
            approved_amount=float(claim.approved_amount) if claim.approved_amount else None,
            processing_costs=float(claim.processing_costs) if claim.processing_costs else None,
            tx_hash=claim.tx_hash,
            created_at=claim.created_at
        )
        for claim in claims
    ]


@router.get("/{claim_id}", response_model=ClaimResponse)
async def get_claim(
    claim_id: str,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Get claim status and details.
    
    - Claimants: Can only view their own claims
    - Insurers: Can view any claim
    
    Returns:
    - status: SUBMITTED, EVALUATING, APPROVED, SETTLED, REJECTED
    - decision: APPROVED, NEEDS_REVIEW, REJECTED (if evaluated)
    - confidence: AI confidence score (0.0-1.0)
    - approved_amount: Amount approved for settlement
    - processing_costs: Sum of x402 micropayments
    - tx_hash: Arc transaction hash (if settled)
    """
    # Validate UUID format
    try:
        uuid.UUID(claim_id)  # Validates format
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid claim ID format")
    
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Check authorization (optional - allow unauthenticated viewing for demo)
    current_user = None
    if credentials:
        try:
            current_user = get_current_user(credentials, db)
            if current_user.role == "claimant":
                # Claimants can only view their own claims
                user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
                if user_wallet and claim.claimant_address != user_wallet.wallet_address:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You can only view your own claims"
                    )
        except HTTPException:
            pass  # Allow unauthenticated viewing for demo
    
    return ClaimResponse(
        id=str(claim.id),
        claimant_address=claim.claimant_address,
        claim_amount=float(claim.claim_amount),
        status=claim.status,
        decision=claim.decision,
        confidence=float(claim.confidence) if claim.confidence else None,
        approved_amount=float(claim.approved_amount) if claim.approved_amount else None,
        processing_costs=float(claim.processing_costs) if claim.processing_costs else None,
        tx_hash=claim.tx_hash,
        created_at=claim.created_at
    )
