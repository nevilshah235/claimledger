"""
Verifier endpoints for document, image, and fraud analysis.

Evaluations are free: no x402, no payment. Callers must send X-Internal-Secret
(used by backend when tools call /verifier/*). Usage is recorded with amount=0
for tracking.

- POST /verifier/document - Document verification
- POST /verifier/image - Image analysis
- POST /verifier/fraud - Fraud detection
"""

import os
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any, Dict

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import X402Receipt, Claim, Evidence
from ..agent.adk_agents import ADKDocumentAgent, ADKImageAgent, ADKFraudAgent

router = APIRouter(prefix="/verifier", tags=["verifier"])

# Internal auth: only our backend sends this. Default for dev; set EVALUATION_INTERNAL_SECRET in prod.
_INTERNAL_SECRET = os.getenv("EVALUATION_INTERNAL_SECRET", "dev-internal-secret")


def _check_internal_secret(x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret")) -> None:
    if not x_internal_secret or x_internal_secret != _INTERNAL_SECRET:
        raise HTTPException(status_code=401, detail="Missing or invalid X-Internal-Secret")


def _record_usage(db: Session, claim_id: str, verifier_type: str) -> None:
    """Record verifier usage with amount=0 (evaluations are free). Keeps X402Receipt for tracking."""
    rec = X402Receipt(
        id=str(uuid.uuid4()),
        claim_id=claim_id,
        verifier_type=verifier_type,
        amount=Decimal("0.00"),
        gateway_payment_id="free",
        gateway_receipt="free",
        created_at=datetime.utcnow(),
    )
    db.add(rec)
    db.commit()


def _persist_verifier_result_metadata(
    *,
    db: Session,
    claim_id: str,
    agent_type: str,
    full_result: Dict[str, Any],
    evidence_file_path: Optional[str] = None,
) -> None:
    """Persist verifier outputs to Evidence.analysis_metadata."""
    if evidence_file_path:
        evidence = (
            db.query(Evidence)
            .filter(Evidence.claim_id == claim_id, Evidence.file_path == evidence_file_path)
            .first()
        )
        if evidence:
            existing = evidence.analysis_metadata or {}
            existing["verifier_result"] = {
                "type": agent_type,
                "result": full_result or {},
                "updated_at": datetime.utcnow().isoformat(),
            }
            evidence.analysis_metadata = existing
            db.add(evidence)
    db.commit()


class DocumentVerificationRequest(BaseModel):
    claim_id: str
    document_path: str


class DocumentVerificationResponse(BaseModel):
    extracted_data: dict
    valid: bool
    verification_id: str


class ImageAnalysisRequest(BaseModel):
    claim_id: str
    image_path: str


class ImageAnalysisResponse(BaseModel):
    damage_assessment: dict
    valid: bool
    analysis_id: str


class FraudCheckRequest(BaseModel):
    claim_id: str


class FraudCheckResponse(BaseModel):
    fraud_score: float
    risk_level: str
    check_id: str


@router.post("/document")
async def verify_document(
    request: DocumentVerificationRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_check_internal_secret),
):
    """Verify a document. Evaluations are free; usage recorded with amount=0."""
    document_agent = ADKDocumentAgent()
    result = await document_agent.analyze(
        request.claim_id,
        [{"file_path": request.document_path}],
    )
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
    _record_usage(db, request.claim_id, "document")

    return DocumentVerificationResponse(
        extracted_data=result.get("extracted_data", {}),
        valid=result.get("valid", False),
        verification_id=verification_id,
    )


@router.post("/image")
async def analyze_image(
    request: ImageAnalysisRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_check_internal_secret),
):
    """Analyze an image. Evaluations are free; usage recorded with amount=0."""
    image_agent = ADKImageAgent()
    result = await image_agent.analyze(
        request.claim_id,
        [{"file_path": request.image_path}],
    )
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
    _record_usage(db, request.claim_id, "image")

    return ImageAnalysisResponse(
        damage_assessment=result.get("damage_assessment", {}),
        valid=result.get("valid", False),
        analysis_id=analysis_id,
    )


@router.post("/fraud")
async def check_fraud(
    request: FraudCheckRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_check_internal_secret),
):
    """Check for fraud. Evaluations are free; usage recorded with amount=0."""
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
        evidence_dicts,
    )
    if not result:
        result = {}
    check_id = result.get("check_id", str(uuid.uuid4()))

    _record_usage(db, request.claim_id, "fraud")

    return FraudCheckResponse(
        fraud_score=result.get("fraud_score", 0.5),
        risk_level=result.get("risk_level", "MEDIUM"),
        check_id=check_id,
    )
