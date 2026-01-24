"""
Claims API endpoints.
POST /claims - Submit claim (metadata + files)
GET /claims/{id} - Get claim status
"""

import uuid
import os
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from fastapi import Depends as FastAPIDepends
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Claim, Evidence, Evaluation, User, UserWallet
from ..api.auth import get_current_user, security

router = APIRouter(prefix="/claims", tags=["claims"])


class ClaimResponse(BaseModel):
    """Response model for claim data."""
    id: str
    claimant_address: str
    claim_amount: float
    description: Optional[str] = None
    status: str
    decision: Optional[str] = None
    confidence: Optional[float] = None
    approved_amount: Optional[float] = None
    processing_costs: Optional[float] = None
    tx_hash: Optional[str] = None
    auto_settled: Optional[bool] = None
    requested_data: Optional[list] = None
    human_review_required: Optional[bool] = False
    decision_overridden: Optional[bool] = False
    review_reasons: Optional[list] = None  # Admin only; reasons for manual review
    contradictions: Optional[list] = None  # Admin only; e.g. amount mismatches
    reasoning: Optional[str] = None  # AI narrative (from latest evaluation)
    created_at: datetime

    class Config:
        from_attributes = True


class ClaimCreateResponse(BaseModel):
    """Response model for claim creation."""
    claim_id: str
    status: str


class RequestDataBody(BaseModel):
    requested_data: List[str]


class OverrideDecisionBody(BaseModel):
    decision: str
    approved_amount: Optional[float] = None
    summary: Optional[str] = None


@router.post("", response_model=ClaimCreateResponse)
async def create_claim(
    claim_amount: float = Form(...),
    description: str = Form(""),
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
        description=description or None,
        status="SUBMITTED",
        processing_costs=Decimal("0"),
        created_at=datetime.utcnow()
    )
    db.add(claim)
    
    # Process and store evidence files
    # Get backend directory (where this file is located)
    backend_dir = Path(__file__).parent.parent.parent
    uploads_dir = backend_dir / "uploads"
    # Ensure uploads directory exists (create parent directories if needed)
    uploads_dir.mkdir(exist_ok=True, parents=True)
    
    for file in files:
        if not file.filename:
            continue  # Skip files without names
        
        # Determine file type
        file_type = "document"
        if file.content_type and file.content_type.startswith("image/"):
            file_type = "image"
        
        # Create claim-specific directory
        claim_dir = uploads_dir / claim_id
        claim_dir.mkdir(exist_ok=True, parents=True)
        
        # Save file to local storage
        # In production, would use IPFS or cloud storage
        # Sanitize filename to prevent path traversal
        safe_filename = file.filename.replace("..", "").replace("/", "_").replace("\\", "_")
        file_path = claim_dir / safe_filename
        
        # Read file content and write to disk
        try:
            file_content = await file.read()
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            # Store absolute path in database (agents need to read files)
            # Use absolute path so agents can find files regardless of working directory
            absolute_path = str(file_path.absolute())
            
            evidence = Evidence(
                id=str(uuid.uuid4()),
                claim_id=claim_id,
                file_type=file_type,
                file_path=absolute_path,
                file_size=len(file_content),
                mime_type=file.content_type,
                created_at=datetime.utcnow()
            )
            db.add(evidence)
        except Exception as e:
            print(f"Error saving file {file.filename}: {e}")
            # Still create evidence record but mark as failed
            evidence = Evidence(
                id=str(uuid.uuid4()),
                claim_id=claim_id,
                file_type=file_type,
                file_path=f"uploads/{claim_id}/{file.filename}",  # Fallback path
                file_size=None,
                mime_type=file.content_type,
                processing_status="FAILED",
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
            description=getattr(claim, "description", None),
            status=claim.status,
            decision=claim.decision,
            confidence=float(claim.confidence) if claim.confidence else None,
            approved_amount=float(claim.approved_amount) if claim.approved_amount else None,
            processing_costs=float(claim.processing_costs) if claim.processing_costs else None,
            tx_hash=claim.tx_hash,
            auto_settled=getattr(claim, "auto_settled", None),
            requested_data=claim.requested_data if hasattr(claim, 'requested_data') else None,
            human_review_required=claim.human_review_required if hasattr(claim, 'human_review_required') else False,
            decision_overridden=getattr(claim, 'decision_overridden', False),
            review_reasons=getattr(claim, 'review_reasons', None),
            contradictions=getattr(claim, 'contradictions', None),
            reasoning=None,
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

    latest_eval = db.query(Evaluation).filter(Evaluation.claim_id == claim_id).order_by(Evaluation.created_at.desc()).first()
    reasoning = latest_eval.reasoning if latest_eval else None

    return ClaimResponse(
        id=str(claim.id),
        claimant_address=claim.claimant_address,
        claim_amount=float(claim.claim_amount),
        description=getattr(claim, "description", None),
        status=claim.status,
        decision=claim.decision,
        confidence=float(claim.confidence) if claim.confidence else None,
        approved_amount=float(claim.approved_amount) if claim.approved_amount else None,
        processing_costs=float(claim.processing_costs) if claim.processing_costs else None,
        tx_hash=claim.tx_hash,
        auto_settled=getattr(claim, "auto_settled", None),
        requested_data=claim.requested_data if hasattr(claim, 'requested_data') else None,
        human_review_required=claim.human_review_required if hasattr(claim, 'human_review_required') else False,
        decision_overridden=getattr(claim, 'decision_overridden', False),
        review_reasons=getattr(claim, 'review_reasons', None),
        contradictions=getattr(claim, 'contradictions', None),
        reasoning=reasoning,
        created_at=claim.created_at
    )


@router.post("/{claim_id}/request-data", response_model=ClaimResponse)
async def request_additional_data(
    claim_id: str,
    body: RequestDataBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Insurer requests additional evidence/info for a claim."""
    if current_user.role != "insurer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only insurers can request data")

    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    claim.requested_data = body.requested_data
    claim.status = "AWAITING_DATA"
    db.commit()
    db.refresh(claim)

    return ClaimResponse(
        id=str(claim.id),
        claimant_address=claim.claimant_address,
        claim_amount=float(claim.claim_amount),
        description=getattr(claim, "description", None),
        status=claim.status,
        decision=claim.decision,
        confidence=float(claim.confidence) if claim.confidence else None,
        approved_amount=float(claim.approved_amount) if claim.approved_amount else None,
        processing_costs=float(claim.processing_costs) if claim.processing_costs else None,
        tx_hash=claim.tx_hash,
        auto_settled=getattr(claim, "auto_settled", None),
        requested_data=claim.requested_data,
        human_review_required=claim.human_review_required if hasattr(claim, 'human_review_required') else False,
        decision_overridden=getattr(claim, 'decision_overridden', False),
        review_reasons=getattr(claim, 'review_reasons', None),
        contradictions=getattr(claim, 'contradictions', None),
        reasoning=None,
        created_at=claim.created_at,
    )


@router.post("/{claim_id}/override-decision", response_model=ClaimResponse)
async def override_decision(
    claim_id: str,
    body: OverrideDecisionBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Insurer overrides AI decision (manual adjudication)."""
    if current_user.role != "insurer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only insurers can override decisions")

    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    claim.decision = body.decision
    claim.decision_overridden = True
    if body.approved_amount is not None:
        claim.approved_amount = Decimal(str(body.approved_amount))
    if body.summary is not None:
        claim.comprehensive_summary = body.summary

    # Best-effort status mapping
    if body.decision in ("APPROVED", "AUTO_APPROVED", "APPROVED_WITH_REVIEW"):
        claim.status = "APPROVED"
    elif body.decision in ("NEEDS_MORE_DATA", "INSUFFICIENT_DATA"):
        claim.status = "AWAITING_DATA"
    elif body.decision in ("REJECTED",):
        claim.status = "REJECTED"
    else:
        claim.status = "NEEDS_REVIEW"

    db.commit()
    db.refresh(claim)

    latest_eval = db.query(Evaluation).filter(Evaluation.claim_id == claim_id).order_by(Evaluation.created_at.desc()).first()
    reasoning = latest_eval.reasoning if latest_eval else None

    return ClaimResponse(
        id=str(claim.id),
        claimant_address=claim.claimant_address,
        claim_amount=float(claim.claim_amount),
        description=getattr(claim, "description", None),
        status=claim.status,
        decision=claim.decision,
        confidence=float(claim.confidence) if claim.confidence else None,
        approved_amount=float(claim.approved_amount) if claim.approved_amount else None,
        processing_costs=float(claim.processing_costs) if claim.processing_costs else None,
        tx_hash=claim.tx_hash,
        auto_settled=getattr(claim, "auto_settled", None),
        requested_data=claim.requested_data if hasattr(claim, 'requested_data') else None,
        human_review_required=claim.human_review_required if hasattr(claim, 'human_review_required') else False,
        decision_overridden=getattr(claim, 'decision_overridden', False),
        review_reasons=getattr(claim, 'review_reasons', None),
        contradictions=getattr(claim, 'contradictions', None),
        reasoning=reasoning,
        created_at=claim.created_at,
    )


@router.post("/{claim_id}/evidence", response_model=ClaimResponse)
async def add_claim_evidence(
    claim_id: str,
    files: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add additional evidence to an existing claim (for 'additional evidence requested' flow).

    Claimants may only add evidence to their own claims.
    """
    if current_user.role != "claimant":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only claimants can add evidence")

    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
    if not user_wallet or claim.claimant_address != user_wallet.wallet_address:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own claims")

    # Store evidence files (same approach as create_claim)
    backend_dir = Path(__file__).parent.parent.parent
    uploads_dir = backend_dir / "uploads"
    uploads_dir.mkdir(exist_ok=True, parents=True)

    claim_dir = uploads_dir / claim_id
    claim_dir.mkdir(exist_ok=True, parents=True)

    for file in files:
        if not file.filename:
            continue

        file_type = "document"
        if file.content_type and file.content_type.startswith("image/"):
            file_type = "image"

        safe_filename = file.filename.replace("..", "").replace("/", "_").replace("\\", "_")
        file_path = claim_dir / safe_filename

        try:
            file_content = await file.read()
            with open(file_path, "wb") as f:
                f.write(file_content)

            absolute_path = str(file_path.absolute())
            evidence = Evidence(
                id=str(uuid.uuid4()),
                claim_id=claim_id,
                file_type=file_type,
                file_path=absolute_path,
                file_size=len(file_content),
                mime_type=file.content_type,
                created_at=datetime.utcnow(),
            )
            db.add(evidence)
        except Exception as e:
            print(f"Error saving file {file.filename}: {e}")
            evidence = Evidence(
                id=str(uuid.uuid4()),
                claim_id=claim_id,
                file_type=file_type,
                file_path=f"uploads/{claim_id}/{file.filename}",
                file_size=None,
                mime_type=file.content_type,
                processing_status="FAILED",
                created_at=datetime.utcnow(),
            )
            db.add(evidence)

    # Clear requested_data and return to submitted so evaluation can restart
    claim.requested_data = None
    claim.status = "SUBMITTED"
    db.commit()
    db.refresh(claim)

    return ClaimResponse(
        id=str(claim.id),
        claimant_address=claim.claimant_address,
        claim_amount=float(claim.claim_amount),
        description=getattr(claim, "description", None),
        status=claim.status,
        decision=claim.decision,
        confidence=float(claim.confidence) if claim.confidence else None,
        approved_amount=float(claim.approved_amount) if claim.approved_amount else None,
        processing_costs=float(claim.processing_costs) if claim.processing_costs else None,
        tx_hash=claim.tx_hash,
        auto_settled=getattr(claim, "auto_settled", None),
        requested_data=claim.requested_data,
        human_review_required=claim.human_review_required if hasattr(claim, "human_review_required") else False,
        decision_overridden=getattr(claim, 'decision_overridden', False),
        review_reasons=getattr(claim, 'review_reasons', None),
        contradictions=getattr(claim, 'contradictions', None),
        reasoning=None,
        created_at=claim.created_at,
    )


@router.post("/{claim_id}/reset-evaluating", response_model=ClaimResponse)
async def reset_evaluating(
    claim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reset a claim stuck in EVALUATING back to SUBMITTED so evaluation can be retried.
    Claimants may only reset their own claims.
    """
    if current_user.role != "claimant":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only claimants can reset their own evaluations")

    try:
        uuid.UUID(claim_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid claim ID format")

    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
    if not user_wallet or claim.claimant_address != user_wallet.wallet_address:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own claims")

    if claim.status != "EVALUATING":
        raise HTTPException(
            status_code=400,
            detail=f"Claim is not stuck in EVALUATING (current status: {claim.status})",
        )

    claim.status = "SUBMITTED"
    db.commit()
    db.refresh(claim)

    return ClaimResponse(
        id=str(claim.id),
        claimant_address=claim.claimant_address,
        claim_amount=float(claim.claim_amount),
        description=getattr(claim, "description", None),
        status=claim.status,
        decision=claim.decision,
        confidence=float(claim.confidence) if claim.confidence else None,
        approved_amount=float(claim.approved_amount) if claim.approved_amount else None,
        processing_costs=float(claim.processing_costs) if claim.processing_costs else None,
        tx_hash=claim.tx_hash,
        auto_settled=getattr(claim, "auto_settled", None),
        requested_data=claim.requested_data if hasattr(claim, "requested_data") else None,
        human_review_required=claim.human_review_required if hasattr(claim, "human_review_required") else False,
        decision_overridden=getattr(claim, "decision_overridden", False),
        review_reasons=getattr(claim, 'review_reasons', None),
        contradictions=getattr(claim, 'contradictions', None),
        reasoning=None,
        created_at=claim.created_at,
    )


class EvidenceItem(BaseModel):
    """Evidence file information."""
    id: str
    file_type: str
    file_path: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/{claim_id}/evidence", response_model=List[EvidenceItem])
async def get_claim_evidence(
    claim_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get list of evidence files for a claim.
    
    - Claimants: Can only view evidence for their own claims
    - Insurers: Can view evidence for any claim
    """
    # Validate UUID format
    try:
        uuid.UUID(claim_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid claim ID format")
    
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Check authorization
    if current_user:
        if current_user.role == "claimant":
            user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
            if user_wallet and claim.claimant_address != user_wallet.wallet_address:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only view evidence for your own claims"
                )
    
    # Get all evidence for this claim
    evidence_list = db.query(Evidence).filter(Evidence.claim_id == claim_id).order_by(Evidence.created_at).all()
    
    return [
        EvidenceItem(
            id=str(ev.id),
            file_type=ev.file_type,
            file_path=ev.file_path,
            file_size=ev.file_size,
            mime_type=ev.mime_type,
            created_at=ev.created_at
        )
        for ev in evidence_list
    ]


@router.get("/{claim_id}/evidence/{evidence_id}/download")
async def download_evidence(
    claim_id: str,
    evidence_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Download/view an evidence file.
    
    - Claimants: Can only download evidence for their own claims
    - Insurers: Can download evidence for any claim
    """
    # Validate UUID format
    try:
        uuid.UUID(claim_id)
        uuid.UUID(evidence_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Check authorization
    if current_user:
        if current_user.role == "claimant":
            user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
            if user_wallet and claim.claimant_address != user_wallet.wallet_address:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only download evidence for your own claims"
                )
    
    # Get evidence record
    evidence = db.query(Evidence).filter(
        Evidence.id == evidence_id,
        Evidence.claim_id == claim_id
    ).first()
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    # Check if file exists
    file_path = Path(evidence.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")
    
    # Determine media type
    media_type = evidence.mime_type or "application/octet-stream"
    
    # Get filename from path
    filename = file_path.name
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename
    )
