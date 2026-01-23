"""
Agent tools for claim evaluation.

1. verify_document - Document verification (free)
2. verify_image - Image analysis (free)
3. verify_fraud - Fraud detection (free)
4. approve_claim - On-chain settlement

Evaluations are free. Settlement uses USDC on Arc.
"""

from typing import Dict, Any
from decimal import Decimal

from ..services.verifier_client import verify_document as _verify_document, verify_image as _verify_image, verify_fraud as _verify_fraud
from ..services.blockchain import get_blockchain_service


async def verify_document(claim_id: str, document_path: str) -> Dict[str, Any]:
    """Verify a document. Evaluations are free."""
    try:
        result = await _verify_document(claim_id, document_path)
        return {
            "success": True,
            "extracted_data": result.get("extracted_data", {}),
            "valid": result.get("valid", False),
            "verification_id": result.get("verification_id"),
            "cost": 0.0,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "cost": 0.0}


async def verify_image(claim_id: str, image_path: str) -> Dict[str, Any]:
    """Analyze an image. Evaluations are free."""
    try:
        result = await _verify_image(claim_id, image_path)
        return {
            "success": True,
            "damage_assessment": result.get("damage_assessment", {}),
            "valid": result.get("valid", False),
            "analysis_id": result.get("analysis_id"),
            "cost": 0.0,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "cost": 0.0}


async def verify_fraud(claim_id: str) -> Dict[str, Any]:
    """Check for fraud. Evaluations are free."""
    try:
        result = await _verify_fraud(claim_id)
        return {
            "success": True,
            "fraud_score": result.get("fraud_score", 0.0),
            "risk_level": result.get("risk_level", "UNKNOWN"),
            "check_id": result.get("check_id"),
            "cost": 0.0,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "cost": 0.0}


async def approve_claim(claim_id: str, amount: float, recipient: str) -> Dict[str, Any]:
    """Approve a claim and trigger USDC settlement on Arc."""
    blockchain = get_blockchain_service()
    try:
        tx_hash = await blockchain.approve_claim(
            claim_id=claim_id,
            amount=Decimal(str(amount)),
            recipient=recipient,
        )
        if tx_hash:
            return {"success": True, "tx_hash": tx_hash, "status": "SETTLED", "amount": amount, "recipient": recipient}
        return {"success": False, "error": "Transaction failed", "status": "FAILED"}
    except Exception as e:
        return {"success": False, "error": str(e), "status": "ERROR"}


# Tool definitions for Google Agents Framework (costs removed; evaluations are free)
TOOL_DEFINITIONS = [
    {
        "name": "verify_document",
        "description": "Verify a document (invoice, receipt, etc.) for authenticity and extract data.",
        "parameters": {
            "type": "object",
            "properties": {"claim_id": {"type": "string"}, "document_path": {"type": "string"}},
            "required": ["claim_id", "document_path"],
        },
    },
    {
        "name": "verify_image",
        "description": "Analyze an image (damage photos, etc.) to assess damage and validity.",
        "parameters": {
            "type": "object",
            "properties": {"claim_id": {"type": "string"}, "image_path": {"type": "string"}},
            "required": ["claim_id", "image_path"],
        },
    },
    {
        "name": "verify_fraud",
        "description": "Check for fraud indicators on a claim.",
        "parameters": {"type": "object", "properties": {"claim_id": {"type": "string"}}, "required": ["claim_id"]},
    },
    {
        "name": "approve_claim",
        "description": "Approve a claim and trigger USDC settlement on Arc. Only call if confidence >= 0.85.",
        "parameters": {
            "type": "object",
            "properties": {"claim_id": {"type": "string"}, "amount": {"type": "number"}, "recipient": {"type": "string"}},
            "required": ["claim_id", "amount", "recipient"],
        },
    },
]
