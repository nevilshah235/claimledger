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
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import X402Receipt
from ..services.gateway import get_gateway_service

router = APIRouter(prefix="/verifier", tags=["verifier"])

# x402 Pricing (in USDC)
DOCUMENT_VERIFICATION_PRICE = Decimal("0.10")
IMAGE_ANALYSIS_PRICE = Decimal("0.15")
FRAUD_CHECK_PRICE = Decimal("0.10")


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
    **Price:** $0.10 USDC
    
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
    
    # Perform document verification (mock for demo)
    # In production, would use OCR/AI to extract and verify document
    verification_id = str(uuid.uuid4())
    
    return DocumentVerificationResponse(
        extracted_data={
            "document_type": "invoice",
            "amount": 3500.00,
            "date": "2024-01-15",
            "vendor": "Auto Repair Shop",
            "description": "Front bumper repair and replacement"
        },
        valid=True,
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
    **Price:** $0.15 USDC
    
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
    
    # Perform image analysis (mock for demo)
    # In production, would use computer vision/AI to analyze damage
    analysis_id = str(uuid.uuid4())
    
    return ImageAnalysisResponse(
        damage_assessment={
            "damage_type": "collision",
            "affected_parts": ["front_bumper", "hood"],
            "severity": "moderate",
            "estimated_cost": 3500.00,
            "confidence": 0.89
        },
        valid=True,
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
    **Price:** $0.10 USDC
    
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
    
    # Perform fraud check (mock for demo)
    # In production, would use ML model to detect fraud patterns
    check_id = str(uuid.uuid4())
    
    # Mock low fraud score for demo happy path
    fraud_score = 0.05
    risk_level = "LOW" if fraud_score < 0.3 else ("MEDIUM" if fraud_score < 0.7 else "HIGH")
    
    return FraudCheckResponse(
        fraud_score=fraud_score,
        risk_level=risk_level,
        check_id=check_id
    )
