"""
Agent Tools.
4 explicit tools for the insurance claim evaluation agent.

1. verify_document - Document verification (x402-paid)
2. verify_image - Image analysis (x402-paid)
3. verify_fraud - Fraud detection (x402-paid)
4. approve_claim - Onchain settlement

Uses Circle Gateway for x402 micropayments.
Uses USDC on Arc for settlement.
"""

from typing import Dict, Any, Optional
from decimal import Decimal

from ..services.x402_client import get_x402_client, X402PaymentError
from ..services.blockchain import get_blockchain_service


async def verify_document(claim_id: str, document_path: str) -> Dict[str, Any]:
    """
    Verify a document (invoice, receipt, etc.).
    
    This tool calls the x402-protected /verifier/document endpoint.
    Payment of $0.10 USDC is handled automatically.
    
    Args:
        claim_id: Unique claim identifier
        document_path: Path to the document file
        
    Returns:
        {
            "extracted_data": {...},
            "valid": bool,
            "verification_id": str
        }
    """
    client = get_x402_client()
    
    try:
        result = await client.verify_document(claim_id, document_path)
        return {
            "success": True,
            "extracted_data": result.get("extracted_data", {}),
            "valid": result.get("valid", False),
            "verification_id": result.get("verification_id"),
            "cost": 0.10
        }
    except X402PaymentError as e:
        return {
            "success": False,
            "error": f"Payment failed: {str(e)}",
            "cost": 0.0
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "cost": 0.0
        }


async def verify_image(claim_id: str, image_path: str) -> Dict[str, Any]:
    """
    Analyze an image (damage photos, etc.).
    
    This tool calls the x402-protected /verifier/image endpoint.
    Payment of $0.15 USDC is handled automatically.
    
    Args:
        claim_id: Unique claim identifier
        image_path: Path to the image file
        
    Returns:
        {
            "damage_assessment": {...},
            "valid": bool,
            "analysis_id": str
        }
    """
    client = get_x402_client()
    
    try:
        result = await client.verify_image(claim_id, image_path)
        return {
            "success": True,
            "damage_assessment": result.get("damage_assessment", {}),
            "valid": result.get("valid", False),
            "analysis_id": result.get("analysis_id"),
            "cost": 0.15
        }
    except X402PaymentError as e:
        return {
            "success": False,
            "error": f"Payment failed: {str(e)}",
            "cost": 0.0
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "cost": 0.0
        }


async def verify_fraud(claim_id: str) -> Dict[str, Any]:
    """
    Check for fraud indicators.
    
    This tool calls the x402-protected /verifier/fraud endpoint.
    Payment of $0.10 USDC is handled automatically.
    
    Args:
        claim_id: Unique claim identifier
        
    Returns:
        {
            "fraud_score": float,
            "risk_level": str,
            "check_id": str
        }
    """
    client = get_x402_client()
    
    try:
        result = await client.verify_fraud(claim_id)
        return {
            "success": True,
            "fraud_score": result.get("fraud_score", 0.0),
            "risk_level": result.get("risk_level", "UNKNOWN"),
            "check_id": result.get("check_id"),
            "cost": 0.10
        }
    except X402PaymentError as e:
        return {
            "success": False,
            "error": f"Payment failed: {str(e)}",
            "cost": 0.0
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "cost": 0.0
        }


async def approve_claim(claim_id: str, amount: float, recipient: str) -> Dict[str, Any]:
    """
    Approve a claim and trigger USDC settlement on Arc.
    
    This tool calls the blockchain service to execute
    ClaimEscrow.approveClaim() on Arc.
    
    Args:
        claim_id: Unique claim identifier
        amount: Amount to settle in USDC
        recipient: Claimant wallet address
        
    Returns:
        {
            "tx_hash": str,
            "status": str
        }
    """
    blockchain = get_blockchain_service()
    
    try:
        tx_hash = await blockchain.approve_claim(
            claim_id=claim_id,
            amount=Decimal(str(amount)),
            recipient=recipient
        )
        
        if tx_hash:
            return {
                "success": True,
                "tx_hash": tx_hash,
                "status": "SETTLED",
                "amount": amount,
                "recipient": recipient
            }
        else:
            return {
                "success": False,
                "error": "Transaction failed",
                "status": "FAILED"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "status": "ERROR"
        }


# Tool definitions for Google Agents Framework
TOOL_DEFINITIONS = [
    {
        "name": "verify_document",
        "description": "Verify a document (invoice, receipt, etc.) for authenticity and extract data. Costs $0.10 USDC.",
        "parameters": {
            "type": "object",
            "properties": {
                "claim_id": {
                    "type": "string",
                    "description": "Unique claim identifier"
                },
                "document_path": {
                    "type": "string",
                    "description": "Path to the document file"
                }
            },
            "required": ["claim_id", "document_path"]
        }
    },
    {
        "name": "verify_image",
        "description": "Analyze an image (damage photos, etc.) to assess damage and validity. Costs $0.15 USDC.",
        "parameters": {
            "type": "object",
            "properties": {
                "claim_id": {
                    "type": "string",
                    "description": "Unique claim identifier"
                },
                "image_path": {
                    "type": "string",
                    "description": "Path to the image file"
                }
            },
            "required": ["claim_id", "image_path"]
        }
    },
    {
        "name": "verify_fraud",
        "description": "Check for fraud indicators on a claim. Costs $0.10 USDC.",
        "parameters": {
            "type": "object",
            "properties": {
                "claim_id": {
                    "type": "string",
                    "description": "Unique claim identifier"
                }
            },
            "required": ["claim_id"]
        }
    },
    {
        "name": "approve_claim",
        "description": "Approve a claim and trigger USDC settlement on Arc blockchain. Only call if confidence >= 0.85.",
        "parameters": {
            "type": "object",
            "properties": {
                "claim_id": {
                    "type": "string",
                    "description": "Unique claim identifier"
                },
                "amount": {
                    "type": "number",
                    "description": "Amount to settle in USDC"
                },
                "recipient": {
                    "type": "string",
                    "description": "Claimant wallet address"
                }
            },
            "required": ["claim_id", "amount", "recipient"]
        }
    }
]
