"""
x402-Protected Verifier Endpoints.
These endpoints return HTTP 402 Payment Required unless a valid payment receipt is provided.

- POST /verifier/document - Document verification ($0.10 USDC)
- POST /verifier/image - Image analysis ($0.15 USDC)
- POST /verifier/fraud - Fraud detection ($0.10 USDC)

Uses Circle Gateway for x402 micropayments.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any, Dict

from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import X402Receipt, Claim, Evidence
from ..services.gateway import get_gateway_service
from ..agent.adk_agents import ADKDocumentAgent, ADKImageAgent, ADKFraudAgent

router = APIRouter(prefix="/verifier", tags=["verifier"])

# x402 Pricing (in USDC) - reduced costs
DOCUMENT_VERIFICATION_PRICE = Decimal("0.05")
IMAGE_ANALYSIS_PRICE = Decimal("0.10")
FRAUD_CHECK_PRICE = Decimal("0.05")


class PaymentRequiredResponse(BaseModel):
    """Response model for HTTP 402 Payment Required."""
    error: str = "Payment required"
    amount: str
    currency: str = "USDC"
    gateway_payment_id: str
    payment_url: str
    description: str


class DocumentVerificationRequest(BaseModel):
    """Request model for document verification."""
    claim_id: str
    document_path: str


class DocumentVerificationResponse(BaseModel):
    """Response model for document verification."""
    extracted_data: dict
    valid: bool
    verification_id: str


class ImageAnalysisRequest(BaseModel):
    """Request model for image analysis."""
    claim_id: str
    image_path: str


class ImageAnalysisResponse(BaseModel):
    """Response model for image analysis."""
    damage_assessment: dict
    valid: bool
    analysis_id: str


class FraudCheckRequest(BaseModel):
    """Request model for fraud detection."""
    claim_id: str


class FraudCheckResponse(BaseModel):
    """Response model for fraud detection."""
    fraud_score: float
    risk_level: str  # LOW, MEDIUM, HIGH
    check_id: str


def _persist_verifier_result_metadata(
    *,
    db: Session,
    claim_id: str,
    agent_type: str,
    full_result: Dict[str, Any],
    evidence_file_path: Optional[str] = None,
) -> None:
    """
    Persist full verifier outputs for file-centric UX/debugging.

    Centralization decision:
    - `AgentResult` rows are stored centrally by `backend/src/api/agent.py`
      when it persists orchestrator/tool results.
    - `/verifier/*` stores only evidence-level metadata (document/image),
      plus `X402Receipt` via `verify_payment_receipt(...)`.

    Evidence-level storage:
    - Store under Evidence.analysis_metadata["verifier_result"] to keep it
      separate from STEP 1 extraction artifacts.
    """
    # Evidence-level persistence (document/image only)
    if evidence_file_path:
        evidence = (
            db.query(Evidence)
            .filter(Evidence.claim_id == claim_id, Evidence.file_path == evidence_file_path)
            .first()
        )
        if evidence:
            existing = evidence.analysis_metadata or {}
            # Keep multi-step artifacts separate: extraction_result vs verifier_result
            existing["verifier_result"] = {
                "type": agent_type,
                "result": full_result or {},
                "updated_at": datetime.utcnow().isoformat(),
            }
            evidence.analysis_metadata = existing
            db.add(evidence)

    db.commit()


async def verify_payment_receipt(
    receipt: Optional[str],
    expected_amount: Decimal,
    verifier_type: str,
    claim_id: str,
    db: Session
) -> bool:
    """
    Verify a payment receipt from Circle Gateway.
    
    Validates the receipt with Circle Gateway API if available,
    otherwise accepts receipts in demo mode.
    
    Args:
        receipt: Payment receipt token from Gateway
        expected_amount: Expected payment amount in USDC
        verifier_type: Type of verifier (document, image, fraud)
        claim_id: Claim ID for tracking
        db: Database session
        
    Returns:
        True if receipt is valid, False otherwise
    """
    if not receipt:
        return False
    
    # Validate receipt with Circle Gateway API
    gateway = get_gateway_service()
    is_valid = await gateway.validate_receipt(receipt)
    
    if not is_valid:
        return False
    
    # Store receipt for audit trail
    # Extract payment ID from receipt (first 36 chars or full receipt)
    payment_id = receipt[:36] if len(receipt) >= 36 else receipt
    
    x402_receipt = X402Receipt(
        id=str(uuid.uuid4()),
        claim_id=claim_id,
        verifier_type=verifier_type,
        amount=expected_amount,
        gateway_payment_id=payment_id,
        gateway_receipt=receipt,
        created_at=datetime.utcnow()
    )
    db.add(x402_receipt)
    db.commit()
    
    return True


def create_402_response(
    amount: Decimal,
    description: str,
    verifier_type: str
) -> JSONResponse:
    """Create HTTP 402 Payment Required response."""
    payment_id = str(uuid.uuid4())
    
    response_data = {
        "error": "Payment required",
        "amount": str(amount),
        "currency": "USDC",
        "gateway_payment_id": payment_id,
        "payment_url": f"https://gateway.circle.com/pay/{payment_id}",
        "description": description
    }
    
    return JSONResponse(
        status_code=402,
        content=response_data,
        headers={
            "X-Payment-Amount": str(amount),
            "X-Payment-Currency": "USDC",
            "X-Payment-Description": description,
            "X-Gateway-Payment-Id": payment_id
        }
    )


@router.post("/document")
async def verify_document(
    request: DocumentVerificationRequest,
    x_payment_receipt: Optional[str] = Header(None, alias="X-Payment-Receipt"),
    db: Session = Depends(get_db)
):
    """
    Verify a document (invoice, receipt, etc.).
    
    **x402 Protected:** Returns HTTP 402 if no valid payment receipt.
    **Price:** $0.05 USDC
    
    Returns extracted data and validity assessment.
    """
    # Check for payment receipt
    receipt_valid = await verify_payment_receipt(
        x_payment_receipt,
        DOCUMENT_VERIFICATION_PRICE,
        "document",
        request.claim_id,
        db
    )
    
    if not receipt_valid:
        return create_402_response(
            DOCUMENT_VERIFICATION_PRICE,
            "Document verification fee",
            "document"
        )
    
    # Use DocumentAgent for real Gemini API analysis
    document_agent = ADKDocumentAgent()
    result = await document_agent.analyze(
        request.claim_id,
        [{"file_path": request.document_path}]
    )
    
    # Handle None result or missing verification_id
    if not result:
        result = {}
    verification_id = result.get("verification_id") or str(uuid.uuid4())

    _persist_verifier_result_metadata(
        db=db,
        claim_id=request.claim_id,
        agent_type="document",
        full_result=result,
        evidence_file_path=request.document_path,
    )
    
    return DocumentVerificationResponse(
        extracted_data=result.get("extracted_data", {}),
        valid=result.get("valid", False),
        verification_id=verification_id
    )


@router.post("/image")
async def analyze_image(
    request: ImageAnalysisRequest,
    x_payment_receipt: Optional[str] = Header(None, alias="X-Payment-Receipt"),
    db: Session = Depends(get_db)
):
    """
    Analyze an image (damage photos, etc.).
    
    **x402 Protected:** Returns HTTP 402 if no valid payment receipt.
    **Price:** $0.10 USDC
    
    Returns damage assessment and validity.
    """
    # Check for payment receipt
    receipt_valid = await verify_payment_receipt(
        x_payment_receipt,
        IMAGE_ANALYSIS_PRICE,
        "image",
        request.claim_id,
        db
    )
    
    if not receipt_valid:
        return create_402_response(
            IMAGE_ANALYSIS_PRICE,
            "Image analysis fee",
            "image"
        )
    
    # Use ImageAgent for real Gemini API analysis
    image_agent = ADKImageAgent()
    result = await image_agent.analyze(
        request.claim_id,
        [{"file_path": request.image_path}]
    )
    
    # Handle None result or missing analysis_id
    if not result:
        result = {}
    analysis_id = result.get("analysis_id") or str(uuid.uuid4())

    _persist_verifier_result_metadata(
        db=db,
        claim_id=request.claim_id,
        agent_type="image",
        full_result=result,
        evidence_file_path=request.image_path,
    )
    
    return ImageAnalysisResponse(
        damage_assessment=result.get("damage_assessment", {}),
        valid=result.get("valid", False),
        analysis_id=analysis_id
    )


@router.post("/fraud")
async def check_fraud(
    request: FraudCheckRequest,
    x_payment_receipt: Optional[str] = Header(None, alias="X-Payment-Receipt"),
    db: Session = Depends(get_db)
):
    """
    Check for fraud indicators.
    
    **x402 Protected:** Returns HTTP 402 if no valid payment receipt.
    **Price:** $0.05 USDC
    
    Returns fraud score and risk level.
    """
    # Check for payment receipt
    receipt_valid = await verify_payment_receipt(
        x_payment_receipt,
        FRAUD_CHECK_PRICE,
        "fraud",
        request.claim_id,
        db
    )
    
    if not receipt_valid:
        return create_402_response(
            FRAUD_CHECK_PRICE,
            "Fraud check fee",
            "fraud"
        )
    
    # Use ADKFraudAgent for real Gemini API analysis
    # Get claim and evidence from database
    claim = db.query(Claim).filter(Claim.id == request.claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    evidence = db.query(Evidence).filter(Evidence.claim_id == request.claim_id).all()
    evidence_dicts = [
        {"file_type": e.file_type, "file_path": e.file_path}
        for e in evidence
    ]
    
    fraud_agent = ADKFraudAgent()
    result = await fraud_agent.analyze(
        request.claim_id,
        claim.claim_amount,
        claim.claimant_address,
        evidence_dicts
    )

    if not result:
        result = {}

    # NOTE: Fraud has no single evidence file to attach metadata to.
    # Claim-level persistence is centralized in `backend/src/api/agent.py`.
    
    check_id = result.get("check_id", str(uuid.uuid4()))
    
    return FraudCheckResponse(
        fraud_score=result.get("fraud_score", 0.5),
        risk_level=result.get("risk_level", "MEDIUM"),
        check_id=check_id
    )
