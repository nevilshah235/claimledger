"""
Blockchain API endpoint.
POST /blockchain/settle/{claimId} - Final USDC settlement on Arc

Uses USDC on Arc for settlement.
Interacts with ClaimEscrow contract.
"""

import uuid
import os
from datetime import datetime
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Claim, User
from ..api.auth import get_current_user
from ..services.circle_wallets import CircleWalletsService

router = APIRouter(prefix="/blockchain", tags=["blockchain"])

# Contract configuration from environment
CLAIM_ESCROW_ADDRESS = os.getenv("CLAIM_ESCROW_ADDRESS", "0x80794995149E5d26F22c36eD56B817CBd8E5d4Fa")
ARC_RPC_URL = os.getenv("ARC_RPC_URL", "https://rpc.testnet.arc.network")
USDC_ADDRESS = os.getenv("USDC_ADDRESS", "0x3600000000000000000000000000000000000000")


class SettlementRequest(BaseModel):
    """Request model for settlement."""
    # Optional parameters
    recipient_override: Optional[str] = None


class SettlementResponse(BaseModel):
    """Response model for settlement."""
    claim_id: str
    tx_hash: str
    amount: float
    recipient: str
    status: str


@router.post("/settle/{claim_id}", response_model=SettlementResponse)
async def settle_claim(
    claim_id: str,
    request: SettlementRequest = SettlementRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Settle an approved claim by transferring USDC on Arc.
    
    Calls ClaimEscrow.approveClaim() to release escrowed USDC to claimant.
    
    Requires authentication as insurer.
    
    Requirements:
    - User must be an insurer
    - Claim must be in APPROVED status
    - approved_amount must be set
    
    Returns transaction hash for verification on Arc explorer.
    """
    # Verify user is an insurer
    if current_user.role != "insurer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only insurers can settle claims"
        )
    # Validate UUID format
    try:
        uuid.UUID(claim_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid claim ID format")
    
    # Get claim (using string ID)
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Verify claim is approved
    if claim.status != "APPROVED":
        raise HTTPException(
            status_code=400,
            detail=f"Claim must be APPROVED to settle. Current status: {claim.status}"
        )
    
    if not claim.approved_amount:
        raise HTTPException(
            status_code=400,
            detail="No approved amount set for this claim"
        )
    
    # Validate Circle App ID before allowing settlement
    circle_service = CircleWalletsService()
    if not circle_service.validate_app_id():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Circle App ID is not configured. Settlement requires valid Circle setup."
        )
    
    # Determine recipient
    recipient = request.recipient_override or claim.claimant_address
    
    # Execute settlement on Arc
    # TODO: Integrate with actual blockchain call
    # For now, mock the transaction for demo
    tx_hash = await execute_settlement(
        claim_id=claim_id,
        amount=claim.approved_amount,
        recipient=recipient
    )
    
    # Update claim status
    claim.status = "SETTLED"
    claim.tx_hash = tx_hash
    db.commit()
    
    return SettlementResponse(
        claim_id=str(claim_id),
        tx_hash=tx_hash,
        amount=float(claim.approved_amount),
        recipient=recipient,
        status="SETTLED"
    )


async def execute_settlement(claim_id: str, amount: Decimal, recipient: str) -> str:
    """
    Execute settlement transaction on Arc blockchain.
    
    Calls ClaimEscrow.approveClaim(claimId, amount, recipient)
    
    In production, this would:
    1. Build transaction data
    2. Sign with insurer wallet
    3. Broadcast to Arc network
    4. Wait for confirmation
    5. Return transaction hash
    """
    # TODO: Implement actual blockchain interaction
    # Using web3.py or similar library
    
    # Mock transaction hash for demo
    # In production, would return actual tx hash from blockchain
    import hashlib
    mock_tx_data = f"{claim_id}-{amount}-{recipient}-{datetime.utcnow().isoformat()}"
    mock_tx_hash = "0x" + hashlib.sha256(mock_tx_data.encode()).hexdigest()
    
    return mock_tx_hash


@router.get("/status/{tx_hash}")
async def get_transaction_status(tx_hash: str):
    """
    Get status of a settlement transaction.
    
    Returns transaction details from Arc blockchain.
    """
    # TODO: Query Arc blockchain for transaction status
    
    return {
        "tx_hash": tx_hash,
        "status": "confirmed",
        "block_number": 21322066,
        "explorer_url": f"https://testnet.arcscan.app/tx/{tx_hash}"
    }
