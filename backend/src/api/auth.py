"""
Authentication API endpoints for Circle Wallets integration.

Endpoints:
- POST /auth/circle/init - Initialize Circle authentication
- POST /auth/circle/complete - Complete authentication and store wallet
- GET /auth/circle/wallet - Get user's wallet address
"""

import uuid
from typing import Optional
import httpx
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import UserWallet
from ..services.circle_wallets import CircleWalletsService

router = APIRouter(prefix="/auth", tags=["auth"])


# Request/Response models
class CircleInitRequest(BaseModel):
    """Request to initialize Circle authentication."""
    user_id: Optional[str] = None  # If not provided, generate UUID


class CircleInitResponse(BaseModel):
    """Response with authentication challenge."""
    user_id: str
    user_token: str
    challenge_id: str
    app_id: str


class CircleCompleteRequest(BaseModel):
    """Request to complete Circle authentication."""
    user_token: str
    wallet_address: str
    circle_wallet_id: Optional[str] = None


class CircleCompleteResponse(BaseModel):
    """Response after completing authentication."""
    success: bool
    wallet_address: str
    user_id: str


class WalletResponse(BaseModel):
    """Response with wallet address."""
    wallet_address: str
    user_id: str


# Dependency to get Circle Wallets service
def get_circle_service() -> CircleWalletsService:
    """Get Circle Wallets service instance."""
    return CircleWalletsService()


@router.post("/circle/init", response_model=CircleInitResponse)
async def init_circle_auth(
    request: CircleInitRequest,
    db: Session = Depends(get_db),
    circle_service: CircleWalletsService = Depends(get_circle_service)
):
    """
    Initialize Circle Wallets authentication.
    
    Creates or retrieves a Circle user and generates an authentication challenge.
    The frontend SDK uses the challengeId to show Circle's authentication UI.
    
    Returns:
    - user_id: Circle user identifier
    - user_token: Token for Circle SDK
    - challenge_id: Challenge ID for frontend SDK
    - app_id: Circle App ID for frontend
    """
    try:
        # Generate user_id if not provided
        user_id = request.user_id or str(uuid.uuid4())
        
        # Create or retrieve user in Circle
        user_data = await circle_service.create_user(user_id)
        user_token = user_data.get("userToken")
        
        if not user_token:
            raise HTTPException(
                status_code=500,
                detail="Failed to get user token from Circle"
            )
        
        # Initialize authentication challenge
        challenge_data = await circle_service.initialize_user(user_id)
        challenge_id = challenge_data.get("challengeId")
        
        if not challenge_id:
            raise HTTPException(
                status_code=500,
                detail="Failed to get challenge ID from Circle"
            )
        
        # Get App ID from environment
        app_id = circle_service.app_id or ""
        
        return CircleInitResponse(
            user_id=user_id,
            user_token=user_token,
            challenge_id=challenge_id,
            app_id=app_id
        )
    
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Circle API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Authentication initialization failed: {str(e)}"
        )


@router.post("/circle/complete", response_model=CircleCompleteResponse)
async def complete_circle_auth(
    request: CircleCompleteRequest,
    db: Session = Depends(get_db),
    circle_service: CircleWalletsService = Depends(get_circle_service)
):
    """
    Complete Circle Wallets authentication.
    
    Called after the frontend SDK successfully authenticates the user.
    Stores the wallet address mapping in the database.
    
    Requires:
    - user_token: Circle user token from init
    - wallet_address: Wallet address from Circle SDK
    - circle_wallet_id: Optional Circle wallet ID
    """
    try:
        # Find existing user wallet by token or create new
        # Note: In production, you'd validate the user_token with Circle
        user_wallet = db.query(UserWallet).filter(
            UserWallet.user_token == request.user_token
        ).first()
        
        if user_wallet:
            # Update existing wallet
            user_wallet.wallet_address = request.wallet_address
            if request.circle_wallet_id:
                user_wallet.circle_wallet_id = request.circle_wallet_id
        else:
            # Create new user wallet mapping
            # Extract user_id from token or generate
            # In production, decode user_token to get user_id
            user_id = str(uuid.uuid4())  # Temporary - should extract from token
            
            user_wallet = UserWallet(
                user_id=user_id,
                wallet_address=request.wallet_address,
                circle_wallet_id=request.circle_wallet_id,
                user_token=request.user_token
            )
            db.add(user_wallet)
        
        db.commit()
        db.refresh(user_wallet)
        
        return CircleCompleteResponse(
            success=True,
            wallet_address=user_wallet.wallet_address,
            user_id=user_wallet.user_id
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete authentication: {str(e)}"
        )


@router.get("/circle/wallet", response_model=WalletResponse)
async def get_wallet(
    user_token: Optional[str] = Header(None, alias="X-User-Token"),
    db: Session = Depends(get_db)
):
    """
    Get user's wallet address.
    
    Requires X-User-Token header with the Circle user token.
    
    Returns:
    - wallet_address: User's wallet address
    - user_id: User identifier
    """
    if not user_token:
        raise HTTPException(
            status_code=401,
            detail="X-User-Token header required"
        )
    
    user_wallet = db.query(UserWallet).filter(
        UserWallet.user_token == user_token
    ).first()
    
    if not user_wallet:
        raise HTTPException(
            status_code=404,
            detail="Wallet not found for user token"
        )
    
    return WalletResponse(
        wallet_address=user_wallet.wallet_address,
        user_id=user_wallet.user_id
    )
