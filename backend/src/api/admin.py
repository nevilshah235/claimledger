"""
Admin API endpoints.
GET /admin/fees - Get admin wallet balance and evaluation fee tracking
GET /admin/status - Check if admin auto-login is available
GET /admin/auto-settle-wallet - Auto-settle (developer) wallet address and balances
"""

from decimal import Decimal
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
import os
import logging
import uuid

from ..database import get_db
from ..models import X402Receipt, Claim, User, UserWallet, SettlementGas
from ..api.auth import get_current_user, get_circle_wallets_service
from ..services.gas_tracking import record_settlement_gas
from ..services import arc_rpc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


class AutoSettleWalletResponse(BaseModel):
    """Response for GET /admin/auto-settle-wallet."""
    configured: bool
    address: Optional[str] = None
    usdc_balance: Optional[float] = None
    eurc_balance: Optional[float] = None
    gas_balance_arc: Optional[float] = None
    message: Optional[str] = None


class FeeBreakdown(BaseModel):
    """Fee breakdown for a single evaluation."""
    claim_id: str
    total_cost: float
    tool_costs: Dict[str, float]  # tool_name -> cost
    timestamp: str


class GasBreakdown(BaseModel):
    """Gas paid for a single settlement transaction."""
    claim_id: str
    tx_hash: str
    gas_used: int
    cost_arc: float
    timestamp: str


class FeeTrackingResponse(BaseModel):
    """Response model for fee tracking."""
    wallet_address: Optional[str]
    current_balance: Optional[Dict[str, Any]] = None  # Balance data from Circle API (same format as /auth/wallet)
    total_spent: float  # Total spent across all evaluations
    total_evaluations: int  # Number of evaluations
    average_cost_per_evaluation: float
    fee_breakdown: List[FeeBreakdown]  # Recent evaluations with costs
    total_gas_arc: float  # Total gas (native token) paid for settlement txs
    gas_breakdown: List[GasBreakdown]  # Per-tx gas


class AdminStatusResponse(BaseModel):
    """Response model for admin status check."""
    admin_wallet_configured: bool
    admin_wallet_address: Optional[str] = None
    admin_user_exists: bool = False
    message: str


class ResetEvaluatingResponse(BaseModel):
    """Response for reset-evaluating stuck claims."""
    claim_id: str
    status: str
    message: str


@router.post("/claims/{claim_id}/reset-evaluating", response_model=ResetEvaluatingResponse)
async def reset_evaluating_claim(
    claim_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Reset a claim stuck in EVALUATING back to SUBMITTED so evaluation can be retried.
    Insurer-only. Use when evaluation has failed or timed out and the claim never left EVALUATING.
    """
    if not current_user or current_user.role != "insurer":
        raise HTTPException(status_code=403, detail="Only insurers can reset stuck evaluations")

    try:
        uuid.UUID(claim_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid claim ID format")

    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status != "EVALUATING":
        raise HTTPException(
            status_code=400,
            detail=f"Claim is not stuck in EVALUATING (current status: {claim.status})",
        )

    claim.status = "SUBMITTED"
    db.commit()

    return ResetEvaluatingResponse(
        claim_id=claim_id,
        status="SUBMITTED",
        message="Claim reset to SUBMITTED. You can trigger evaluation again.",
    )


@router.get("/status", response_model=AdminStatusResponse)
async def get_admin_status(
    db: Session = Depends(get_db)
):
    """
    Check if admin auto-login is available.
    
    Returns:
    - admin_wallet_configured: Whether ADMIN_WALLET_ADDRESS is set
    - admin_wallet_address: The configured wallet address (first 10 chars if configured)
    - admin_user_exists: Whether an admin user exists in DB (with or without ADMIN_WALLET_ADDRESS)
    """
    admin_wallet_address = os.getenv("ADMIN_WALLET_ADDRESS")
    
    # Check if any insurer user exists in DB
    insurer_user = db.query(User).filter(User.role == "insurer").first()
    admin_user_exists = insurer_user is not None
    
    if not admin_wallet_address:
        # Check if we can use existing insurer user
        if admin_user_exists:
            user_wallet = db.query(UserWallet).filter(UserWallet.user_id == insurer_user.id).first()
            if user_wallet:
                return AdminStatusResponse(
                    admin_wallet_configured=False,
                    admin_wallet_address=f"{user_wallet.wallet_address[:10]}..." if len(user_wallet.wallet_address) > 10 else user_wallet.wallet_address,
                    admin_user_exists=True,
                    message=f"Admin auto-login is available using existing admin account: {insurer_user.email}"
                )
            else:
                return AdminStatusResponse(
                    admin_wallet_configured=False,
                    admin_wallet_address=None,
                    admin_user_exists=True,
                    message=f"Admin user '{insurer_user.email}' exists but has no wallet. Set ADMIN_WALLET_ADDRESS or complete wallet setup."
                )
        else:
            return AdminStatusResponse(
                admin_wallet_configured=False,
                admin_wallet_address=None,
                admin_user_exists=False,
                message="ADMIN_WALLET_ADDRESS not set and no admin account found. Set ADMIN_WALLET_ADDRESS or create an insurer account first."
            )
    
    # ADMIN_WALLET_ADDRESS is set - check if user exists with this wallet
    user_wallet = db.query(UserWallet).filter(
        UserWallet.wallet_address == admin_wallet_address
    ).first()
    
    wallet_user_exists = user_wallet is not None
    
    return AdminStatusResponse(
        admin_wallet_configured=True,
        admin_wallet_address=f"{admin_wallet_address[:10]}..." if len(admin_wallet_address) > 10 else admin_wallet_address,
        admin_user_exists=wallet_user_exists or admin_user_exists,
        message="Admin auto-login is available. User will be auto-created on first login." if not wallet_user_exists 
                else "Admin auto-login is available. Admin user already exists in database."
    )


@router.get("/auto-settle-wallet", response_model=AutoSettleWalletResponse)
async def get_auto_settle_wallet(
    current_user=Depends(get_current_user),
):
    """
    Get auto-settle (developer) wallet address and balances.
    Used when the AI auto-approves a claim; requires AUTO_SETTLE_PRIVATE_KEY.
    Insurer-only.
    """
    if not current_user or current_user.role != "insurer":
        raise HTTPException(status_code=403, detail="Only insurers can access auto-settle wallet")

    pk = os.getenv("AUTO_SETTLE_PRIVATE_KEY")
    if not pk or not pk.strip():
        return AutoSettleWalletResponse(
            configured=False,
            message="Set AUTO_SETTLE_PRIVATE_KEY to enable auto-settlement.",
        )

    try:
        from eth_account import Account
        acct = Account.from_key(pk)
        address = acct.address
    except Exception as e:
        logger.warning("get_auto_settle_wallet: invalid key: %s", e)
        return AutoSettleWalletResponse(
            configured=False,
            message="AUTO_SETTLE_PRIVATE_KEY is set but invalid. Check the key format.",
        )

    usdc = arc_rpc.usdc_balance_of(address)
    # eurc = arc_rpc.eurc_balance_of(address)  # EURC commented out for now
    gas_wei = arc_rpc.get_balance_wei(address)
    gas_arc = float(gas_wei) / 1e18 if gas_wei is not None else None

    return AutoSettleWalletResponse(
        configured=True,
        address=address,
        usdc_balance=float(usdc) if usdc is not None else None,
        # eurc_balance=float(eurc) if eurc is not None else None,  # EURC commented out
        gas_balance_arc=gas_arc,
    )


@router.get("/fees", response_model=FeeTrackingResponse)
async def get_fee_tracking(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get admin wallet balance and evaluation fee tracking.
    
    Returns:
    - Current wallet balance (from Circle Gateway)
    - Total spent on evaluations
    - Per-evaluation breakdown
    - Recent fee history
    """
    # Only insurers can access this endpoint
    if not current_user or current_user.role != "insurer":
        raise HTTPException(status_code=403, detail="Only insurers can access fee tracking")
    
    # Use the same simple wallet lookup as /auth/wallet (which works correctly)
    # This ensures consistency between "View Wallet" modal and "AI Evaluation Fees"
    user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
    
    if not user_wallet:
        logger.warning(
            f"Admin fee tracking: User {current_user.id} ({current_user.email}) has no wallet address configured"
        )
        return FeeTrackingResponse(
            wallet_address=None,
            current_balance=None,
            total_spent=0.0,
            total_evaluations=0,
            average_cost_per_evaluation=0.0,
            fee_breakdown=[],
            total_gas_arc=0.0,
            gas_breakdown=[],
        )
    
    wallet_address = user_wallet.wallet_address
    
    # Get current balance from Circle Wallets API (same format as /auth/wallet)
    # Return the full balance data structure, let frontend extract USDC balance
    circle_service = get_circle_wallets_service()
    current_balance = None
    
    try:
        if user_wallet.circle_wallet_id and circle_service.api_key:
            logger.info(
                f"Fetching Circle Wallets balance for wallet {wallet_address[:10]}... "
                f"(Circle ID: {user_wallet.circle_wallet_id})"
            )
            user_token = None
            try:
                token_data = await circle_service.create_user_token(str(current_user.id))
                user_token = token_data.get("userToken") or token_data.get("user_token")
            except Exception as e:
                logger.warning(f"Could not create user token for balance fetch: {e}")
            try:
                # User-controlled wallets require X-User-Token; pass user_token
                balance_data = await circle_service.get_wallet_balance(
                    user_wallet.circle_wallet_id,
                    chain="ARC",
                    user_token=user_token,
                )
                logger.info(f"Balance data received: {balance_data}")
                # Return full balance data structure (same as /auth/wallet)
                current_balance = balance_data
            except Exception as e:
                logger.error(f"Could not fetch balance from Circle: {e}", exc_info=True)
                # Return empty balance structure on error (same as /auth/wallet)
                current_balance = {
                    "balances": [],
                    "wallet_id": user_wallet.circle_wallet_id
                }
    except Exception as e:
        logger.error(
            f"Error in balance fetching logic for wallet {wallet_address[:10]}...: {e}",
            exc_info=True
        )
        # Balance fetch is optional, continue without it
        current_balance = None
    
    # Query X402Receipts to calculate spending
    # Note: We need to track which receipts belong to this insurer's evaluations
    # For now, we'll query all receipts and group by claim_id
    # In a production system, you might want to add a wallet_address field to X402Receipt
    # or track which insurer initiated each evaluation
    
    # Get all receipts (grouped by claim_id)
    receipts_query = db.query(
        X402Receipt.claim_id,
        func.sum(X402Receipt.amount).label('total_amount'),
        func.count(X402Receipt.id).label('receipt_count'),
        func.max(X402Receipt.created_at).label('latest_receipt')
    ).group_by(X402Receipt.claim_id)
    
    receipts_data = receipts_query.all()
    
    # Calculate totals
    total_spent = sum(float(row.total_amount) for row in receipts_data)
    total_evaluations = len(receipts_data)
    average_cost = total_spent / total_evaluations if total_evaluations > 0 else 0.0
    
    # Build fee breakdown for recent evaluations (last 20)
    fee_breakdown = []
    for row in receipts_data[:20]:  # Limit to 20 most recent
        claim_id = row.claim_id
        
        # Get individual tool costs for this claim
        claim_receipts = db.query(X402Receipt).filter(
            X402Receipt.claim_id == claim_id
        ).all()
        
        tool_costs = {}
        for receipt in claim_receipts:
            tool_name = f"verify_{receipt.verifier_type}"
            tool_costs[tool_name] = float(receipt.amount)
        
        fee_breakdown.append(FeeBreakdown(
            claim_id=claim_id,
            total_cost=float(row.total_amount),
            tool_costs=tool_costs,
            timestamp=row.latest_receipt.isoformat() if row.latest_receipt else ""
        ))

    # --- Settlement gas: backfill missing, then aggregate ---
    settled = db.query(Claim).filter(Claim.status == "SETTLED", Claim.tx_hash.isnot(None)).all()
    for c in settled:
        if c.tx_hash and not db.query(SettlementGas).filter(SettlementGas.tx_hash == c.tx_hash).first():
            record_settlement_gas(str(c.id), c.tx_hash, db)

    total_gas_arc = float(db.query(func.sum(SettlementGas.cost_arc)).scalar() or 0)
    gas_rows = db.query(SettlementGas).order_by(SettlementGas.created_at.desc()).limit(20).all()
    gas_breakdown = [
        GasBreakdown(
            claim_id=g.claim_id,
            tx_hash=g.tx_hash,
            gas_used=g.gas_used,
            cost_arc=float(g.cost_arc),
            timestamp=g.created_at.isoformat() if g.created_at else "",
        )
        for g in gas_rows
    ]
    
    return FeeTrackingResponse(
        wallet_address=wallet_address,
        current_balance=current_balance,
        total_spent=total_spent,
        total_evaluations=total_evaluations,
        average_cost_per_evaluation=average_cost,
        fee_breakdown=fee_breakdown,
        total_gas_arc=total_gas_arc,
        gas_breakdown=gas_breakdown,
    )
