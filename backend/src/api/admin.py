"""
Admin API endpoints.
GET /admin/fees - Get admin wallet balance and evaluation fee tracking
GET /admin/status - Check if admin auto-login is available
"""

from decimal import Decimal
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
import os
import logging

from ..database import get_db
from ..models import X402Receipt, Claim, User, UserWallet
from ..api.auth import get_current_user, get_circle_wallets_service
from ..services.gateway import get_gateway_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


class FeeBreakdown(BaseModel):
    """Fee breakdown for a single evaluation."""
    claim_id: str
    total_cost: float
    tool_costs: Dict[str, float]  # tool_name -> cost
    timestamp: str


class FeeTrackingResponse(BaseModel):
    """Response model for fee tracking."""
    wallet_address: Optional[str]
    current_balance: Optional[float]  # USDC balance from Gateway
    total_spent: float  # Total spent across all evaluations
    total_evaluations: int  # Number of evaluations
    average_cost_per_evaluation: float
    fee_breakdown: List[FeeBreakdown]  # Recent evaluations with costs


class AdminStatusResponse(BaseModel):
    """Response model for admin status check."""
    admin_wallet_configured: bool
    admin_wallet_address: Optional[str] = None
    admin_user_exists: bool = False
    message: str


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
    
    # Get wallet address - prioritize ADMIN_WALLET_ADDRESS (used for agent operations)
    # Otherwise fall back to user's wallet from database
    admin_wallet_address = os.getenv("ADMIN_WALLET_ADDRESS")
    wallet_address = None
    
    if admin_wallet_address:
        # Use ADMIN_WALLET_ADDRESS if configured (this is the wallet used for agent operations)
        wallet_address = admin_wallet_address
        logger.info(f"Using ADMIN_WALLET_ADDRESS for fee tracking: {wallet_address[:10]}...")
    else:
        # Fall back to user's wallet from database
        user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
        wallet_address = user_wallet.wallet_address if user_wallet else None
        
        if not wallet_address:
            logger.warning(
                f"Admin fee tracking: User {current_user.id} ({current_user.email}) has no wallet address configured"
            )
            return FeeTrackingResponse(
                wallet_address=None,
                current_balance=None,
                total_spent=0.0,
                total_evaluations=0,
                average_cost_per_evaluation=0.0,
                fee_breakdown=[]
            )
    
    # Get current balance from Circle Wallets API (same as wallet info modal)
    # This shows the actual wallet balance, not Gateway balance
    circle_service = get_circle_wallets_service()
    current_balance = None
    balance_float = None
    
    try:
        # Find the UserWallet record to get circle_wallet_id
        user_wallet = db.query(UserWallet).filter(
            UserWallet.wallet_address == wallet_address
        ).first()
        
        # If ADMIN_WALLET_ADDRESS is set but no UserWallet found, try using current user's wallet
        # (in case they're the same address but ADMIN_WALLET_ADDRESS was set manually)
        if not user_wallet and current_user:
            user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
            if user_wallet and user_wallet.wallet_address == wallet_address:
                logger.info(
                    f"Using current user's wallet record for ADMIN_WALLET_ADDRESS {wallet_address[:10]}..."
                )
        
        if user_wallet and user_wallet.circle_wallet_id:
            logger.info(
                f"Fetching Circle Wallets balance for wallet {wallet_address[:10]}... "
                f"(Circle ID: {user_wallet.circle_wallet_id})"
            )
            balance_data = await circle_service.get_wallet_balance(
                user_wallet.circle_wallet_id,
                chain="ARC"
            )
            
            logger.info(f"Balance API response: {balance_data}")
            
            # Extract USDC balance from token balances
            token_balances = balance_data.get("balances", [])
            logger.info(f"Found {len(token_balances)} token balance(s) for wallet {wallet_address[:10]}...")
            
            if token_balances:
                for tb in token_balances:
                    token = tb.get("token", {})
                    symbol = token.get("symbol", "").upper()
                    amount_raw = tb.get("amount", "0")
                    logger.info(
                        f"Checking token: {symbol}, raw amount: {amount_raw}, "
                        f"token data: {token}"
                    )
                    if "USDC" in symbol:
                        # Amount is in raw units (6 decimals for USDC)
                        decimals = token.get("decimals", 6)
                        # Convert from raw units to decimal
                        balance_float = float(amount_raw) / (10 ** decimals)
                        logger.info(
                            f"Circle Wallets balance fetched successfully: {balance_float} USDC "
                            f"for wallet {wallet_address[:10]}... (raw: {amount_raw}, decimals: {decimals})"
                        )
                        break
                
                if balance_float is None:
                    logger.warning(
                        f"No USDC balance found in token balances for wallet {wallet_address[:10]}... "
                        f"Available tokens: {[tb.get('token', {}).get('symbol', 'UNKNOWN') for tb in token_balances]}"
                    )
            else:
                logger.warning(
                    f"No token balances found for wallet {wallet_address[:10]}... "
                    f"Balance data: {balance_data}"
                )
        else:
            if not user_wallet:
                logger.warning(
                    f"No UserWallet record found for wallet {wallet_address[:10]}... - "
                    "cannot fetch balance from Circle Wallets API"
                )
            elif not user_wallet.circle_wallet_id:
                logger.warning(
                    f"UserWallet record exists for {wallet_address[:10]}... but circle_wallet_id is missing - "
                    "cannot fetch balance from Circle Wallets API"
                )
    except Exception as e:
        logger.error(
            f"Failed to fetch Circle Wallets balance for wallet {wallet_address[:10]}...: {e}",
            exc_info=True
        )
        # Continue without balance - don't fail the entire request
        balance_float = None
    
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
    
    return FeeTrackingResponse(
        wallet_address=wallet_address,
        current_balance=balance_float,
        total_spent=total_spent,
        total_evaluations=total_evaluations,
        average_cost_per_evaluation=average_cost,
        fee_breakdown=fee_breakdown
    )
