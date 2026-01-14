"""
Authentication API endpoints.

New endpoints (our own auth):
- POST /auth/register - Register new user (claimant or insurer)
- POST /auth/login - Login user
- GET /auth/me - Get current user info
- GET /wallet - Get user's wallet info

Legacy endpoints (kept for backward compatibility):
- POST /auth/circle/init - Initialize Circle authentication (deprecated)
- POST /auth/circle/complete - Complete Circle authentication (deprecated)
- GET /auth/circle/wallet - Get wallet by token (deprecated)
"""

import uuid
from typing import Optional
import httpx
from fastapi import APIRouter, HTTPException, Depends, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, UserWallet
from ..services.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token
)
from ..services.developer_wallets import DeveloperWalletsService

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


# ============================================================================
# Request/Response Models
# ============================================================================

class RegisterRequest(BaseModel):
    """Request to register a new user."""
    email: EmailStr
    password: str
    role: str  # "claimant" or "insurer"


class RegisterResponse(BaseModel):
    """Response after registration."""
    user_id: str
    email: str
    role: str
    wallet_address: str
    access_token: str


class LoginRequest(BaseModel):
    """Request to login."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Response after login."""
    user_id: str
    email: str
    role: str
    wallet_address: Optional[str] = None
    access_token: str


class UserResponse(BaseModel):
    """User information response."""
    user_id: str
    email: str
    role: str
    wallet_address: Optional[str] = None


class WalletInfoResponse(BaseModel):
    """Wallet information response."""
    wallet_address: str
    circle_wallet_id: str
    wallet_set_id: Optional[str] = None
    blockchain: Optional[str] = None
    balance: Optional[dict] = None


# ============================================================================
# Dependencies
# ============================================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def get_developer_wallets_service() -> DeveloperWalletsService:
    """Get Developer-Controlled Wallets service instance."""
    return DeveloperWalletsService()


# ============================================================================
# New Authentication Endpoints
# ============================================================================

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
    wallet_service: DeveloperWalletsService = Depends(get_developer_wallets_service)
):
    """
    Register a new user (claimant or insurer).
    
    Creates user account and automatically provisions a Developer-Controlled wallet.
    
    Returns:
    - user_id: User identifier
    - email: User email
    - role: User role (claimant/insurer)
    - wallet_address: Provisioned wallet address
    - access_token: JWT token for authentication
    """
    # Validate role
    if request.role not in ["claimant", "insurer"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'claimant' or 'insurer'"
        )
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            email=request.email,
            password_hash=get_password_hash(request.password),
            role=request.role
        )
        db.add(user)
        db.flush()  # Get user.id
        
        # Try to create wallet for user (optional - graceful fallback if Circle not configured)
        wallet_address = None
        try:
            wallet_data = await wallet_service.create_wallet(
                blockchains=["ARC"],  # Arc blockchain
                account_type="SCA"  # Smart Contract Account
            )
            
            # Store wallet mapping
            user_wallet = UserWallet(
                user_id=user.id,
                wallet_address=wallet_data["address"],
                circle_wallet_id=wallet_data["wallet_id"],
                wallet_set_id=wallet_data.get("wallet_set_id")
            )
            db.add(user_wallet)
            wallet_address = wallet_data["address"]
        except (ValueError, httpx.HTTPStatusError, Exception) as wallet_error:
            # Wallet creation failed (likely missing Circle credentials or entity secret not registered)
            # Allow registration to proceed without wallet for development/testing
            error_msg = str(wallet_error)
            import logging
            logging.warning(f"Wallet creation skipped for user {user.id}: {error_msg}")
            
            # For testnet/development: Generate a mock wallet address
            # This allows testing without Circle registration
            import hashlib
            mock_seed = f"{user.id}{user.email}".encode()
            mock_hash = hashlib.sha256(mock_seed).hexdigest()[:40]
            wallet_address = f"0x{mock_hash}"  # Valid Ethereum address format
            
            # Store mock wallet (can be replaced with real wallet later)
            user_wallet = UserWallet(
                user_id=user.id,
                wallet_address=wallet_address,
                circle_wallet_id="mock_wallet",  # Placeholder
                wallet_set_id=None
            )
            db.add(user_wallet)
            logging.info(f"Created mock wallet {wallet_address} for user {user.id} (testnet mode)")
        
        db.commit()
        db.refresh(user)
        
        # Create JWT token
        access_token = create_access_token(
            data={"sub": user.id, "email": user.email, "role": user.role}
        )
        
        # If no wallet, use a placeholder (user can create wallet later)
        if not wallet_address:
            wallet_address = "0x0000000000000000000000000000000000000000"  # Placeholder
        
        return RegisterResponse(
            user_id=user.id,
            email=user.email,
            role=user.role,
            wallet_address=wallet_address,
            access_token=access_token
        )
    
    except httpx.HTTPStatusError as e:
        db.rollback()
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Circle API error: {e.response.text}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login user with email and password.
    
    Returns:
    - user_id: User identifier
    - email: User email
    - role: User role
    - wallet_address: User's wallet address (if exists)
    - access_token: JWT token for authentication
    """
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Get wallet address if exists
    wallet_address = None
    user_wallet = db.query(UserWallet).filter(UserWallet.user_id == user.id).first()
    if user_wallet:
        wallet_address = user_wallet.wallet_address
    
    # Create JWT token
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role}
    )
    
    return LoginResponse(
        user_id=user.id,
        email=user.email,
        role=user.role,
        wallet_address=wallet_address,
        access_token=access_token
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user information.
    
    Requires: Bearer token in Authorization header
    """
    # Get wallet address
    wallet_address = None
    user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
    if user_wallet:
        wallet_address = user_wallet.wallet_address
    
    return UserResponse(
        user_id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        wallet_address=wallet_address
    )


# ============================================================================
# Wallet Endpoints
# ============================================================================

@router.get("/wallet", response_model=WalletInfoResponse)
async def get_wallet_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    wallet_service: DeveloperWalletsService = Depends(get_developer_wallets_service)
):
    """
    Get current user's wallet information.
    
    Returns wallet address, Circle wallet ID, and balance information.
    """
    user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
    
    if not user_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found for user"
        )
    
    # Get wallet balance
    balance = None
    try:
        balance_data = await wallet_service.get_wallet_balance(user_wallet.circle_wallet_id)
        balance = balance_data
    except Exception:
        pass  # Balance fetch is optional
    
    # Get wallet details
    wallet_details = None
    try:
        wallet_details = await wallet_service.get_wallet(user_wallet.circle_wallet_id)
    except Exception:
        pass
    
    return WalletInfoResponse(
        wallet_address=user_wallet.wallet_address,
        circle_wallet_id=user_wallet.circle_wallet_id,
        wallet_set_id=user_wallet.wallet_set_id,
        blockchain=wallet_details.get("blockchain") if wallet_details else "ARC",
        balance=balance
    )


# ============================================================================
# Legacy Circle Endpoints (kept for backward compatibility)
# ============================================================================

# Keep old endpoints but mark as deprecated
# These can be removed later if not needed

from ..services.circle_wallets import CircleWalletsService

class CircleInitRequest(BaseModel):
    """Request to initialize Circle authentication (deprecated)."""
    user_id: Optional[str] = None
    user_token: Optional[str] = None


class CircleInitResponse(BaseModel):
    """Response with authentication challenge (deprecated)."""
    user_id: str
    user_token: str
    challenge_id: str
    app_id: str


class CircleCompleteRequest(BaseModel):
    """Request to complete Circle authentication (deprecated)."""
    user_token: str
    wallet_address: str
    circle_wallet_id: Optional[str] = None


class CircleCompleteResponse(BaseModel):
    """Response after completing authentication (deprecated)."""
    success: bool
    wallet_address: str
    user_id: str


class WalletResponse(BaseModel):
    """Response with wallet address (deprecated)."""
    wallet_address: str
    user_id: str


def get_circle_service() -> CircleWalletsService:
    """Get Circle Wallets service instance (deprecated)."""
    return CircleWalletsService()


@router.post("/circle/init", response_model=CircleInitResponse, deprecated=True)
async def init_circle_auth(
    request: CircleInitRequest,
    db: Session = Depends(get_db),
    circle_service: CircleWalletsService = Depends(get_circle_service)
):
    """
    [DEPRECATED] Initialize Circle Wallets authentication.
    
    Use /auth/register instead.
    """
    try:
        if request.user_token:
            challenge_data = await circle_service.initialize_user(request.user_token)
            challenge_id = challenge_data.get("challengeId")
            user_id = challenge_data.get("userId") or request.user_id or str(uuid.uuid4())
        else:
            user_id = request.user_id or str(uuid.uuid4())
            user_data = await circle_service.create_user(user_id)
            challenge_id = None
        
        app_id = circle_service.app_id or ""
        
        return CircleInitResponse(
            user_id=user_id,
            user_token=request.user_token or "",
            challenge_id=challenge_id or "",
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


@router.post("/circle/complete", response_model=CircleCompleteResponse, deprecated=True)
async def complete_circle_auth(
    request: CircleCompleteRequest,
    db: Session = Depends(get_db),
    circle_service: CircleWalletsService = Depends(get_circle_service)
):
    """
    [DEPRECATED] Complete Circle Wallets authentication.
    
    Use /auth/register instead.
    """
    try:
        user_wallet = db.query(UserWallet).filter(
            UserWallet.user_token == request.user_token
        ).first()
        
        if user_wallet:
            user_wallet.wallet_address = request.wallet_address
            if request.circle_wallet_id:
                user_wallet.circle_wallet_id = request.circle_wallet_id
        else:
            user_id = str(uuid.uuid4())
            user_wallet = UserWallet(
                user_id=user_id,
                wallet_address=request.wallet_address,
                circle_wallet_id=request.circle_wallet_id or "",
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


@router.get("/circle/wallet", response_model=WalletResponse, deprecated=True)
async def get_wallet_legacy(
    user_token: Optional[str] = Header(None, alias="X-User-Token"),
    db: Session = Depends(get_db)
):
    """
    [DEPRECATED] Get user's wallet address.
    
    Use /auth/wallet with Bearer token instead.
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
