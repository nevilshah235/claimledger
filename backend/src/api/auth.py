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
from typing import Optional, Dict, Any
from datetime import datetime
import httpx
import os
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
from ..services.circle_wallets import CircleWalletsService

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


def get_circle_wallets_service() -> CircleWalletsService:
    """Get User-Controlled Wallets service instance."""
    return CircleWalletsService()


# ============================================================================
# New Authentication Endpoints
# ============================================================================

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
    circle_service: CircleWalletsService = Depends(get_circle_wallets_service)
):
    """
    Register a new user (claimant or insurer).
    
    Creates user account and Circle user account for User-Controlled wallets with PIN.
    Wallets are created when users log in and complete PIN challenge via frontend SDK.
    
    Returns:
    - user_id: User identifier
    - email: User email
    - role: User role (claimant/insurer)
    - wallet_address: Will be set when user creates wallet via frontend (placeholder initially)
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
        
        # Create Circle user account for User-Controlled wallets
        # Note: Wallets are created when users log in and complete PIN challenge via frontend SDK
        wallet_address = None
        try:
            if circle_service.app_id:
                # Create Circle user account
                circle_user = await circle_service.create_user(user.id)
                import logging
                logging.info(f"Created Circle user for {user.email}: {circle_user.get('id')}")
            else:
                import logging
                logging.warning(f"CIRCLE_APP_ID not set - Circle user not created for {user.email}")
        except httpx.HTTPStatusError as circle_error:
            # User might already exist in Circle (409) - that's OK
            if circle_error.response.status_code == 409:
                import logging
                logging.info(f"Circle user already exists for {user.email}")
            else:
                import logging
                logging.warning(f"Circle user creation failed for {user.email}: {circle_error.response.status_code}")
        except Exception as circle_error:
            import logging
            logging.warning(f"Circle user creation error for {user.email}: {circle_error}")
        
        db.commit()
        db.refresh(user)
        
        # Create JWT token
        access_token = create_access_token(
            data={"sub": user.id, "email": user.email, "role": user.role}
        )
        
        # Wallet will be created when user logs in and completes PIN challenge
        # Use placeholder for now
        wallet_address = "0x0000000000000000000000000000000000000000"  # Placeholder until wallet created
        
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
            detail="No account found with this email"
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
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


@router.post("/admin/login", response_model=LoginResponse)
async def admin_auto_login(
    db: Session = Depends(get_db)
):
    """
    Auto-login as admin.
    
    This endpoint allows quick access to the admin/insurer interface.
    It works in two modes:
    1. If ADMIN_WALLET_ADDRESS is set: Uses that specific wallet address
    2. If not set: Uses the first existing insurer user with a wallet from the database
    
    Returns:
    - user_id: Admin user identifier
    - email: Admin email
    - role: "insurer"
    - wallet_address: Admin wallet address
    - access_token: JWT token for authentication
    """
    admin_wallet_address = os.getenv("ADMIN_WALLET_ADDRESS")
    
    # If ADMIN_WALLET_ADDRESS is set, use it
    if admin_wallet_address:
        # Find or create admin user with this wallet address
        # Look for existing user with this wallet
        user_wallet = db.query(UserWallet).filter(
            UserWallet.wallet_address == admin_wallet_address
        ).first()
        
        if user_wallet:
            # User exists, get the user
            user = db.query(User).filter(User.id == user_wallet.user_id).first()
            if user and user.role == "insurer":
                # Create JWT token
                access_token = create_access_token(
                    data={"sub": user.id, "email": user.email, "role": user.role}
                )
                return LoginResponse(
                    user_id=user.id,
                    email=user.email,
                    role=user.role,
                    wallet_address=admin_wallet_address,
                    access_token=access_token
                )
        
        # Create new admin user if doesn't exist
        # Generate a placeholder email based on wallet address
        admin_email = f"admin_{admin_wallet_address[:8]}@admin.local"
        
        # Check if user with this email exists
        existing_user = db.query(User).filter(User.email == admin_email).first()
        if existing_user:
            # Update wallet if needed
            if not user_wallet:
                user_wallet = UserWallet(
                    id=str(uuid.uuid4()),
                    user_id=existing_user.id,
                    wallet_address=admin_wallet_address,
                    circle_wallet_id="admin_wallet",  # Placeholder for admin wallet
                    created_at=datetime.utcnow()
                )
                db.add(user_wallet)
                db.commit()
            
            access_token = create_access_token(
                data={"sub": existing_user.id, "email": existing_user.email, "role": existing_user.role}
            )
            return LoginResponse(
                user_id=existing_user.id,
                email=existing_user.email,
                role=existing_user.role,
                wallet_address=admin_wallet_address,
                access_token=access_token
            )
        
        # Create new admin user
        import secrets
        # Generate a random password (not used for auto-login, but required for user model)
        random_password = secrets.token_urlsafe(32)
        password_hash = get_password_hash(random_password)
        
        user = User(
            id=str(uuid.uuid4()),
            email=admin_email,
            password_hash=password_hash,
            role="insurer",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(user)
        db.flush()  # Get user.id
        
        # Create wallet entry
        user_wallet = UserWallet(
            id=str(uuid.uuid4()),
            user_id=user.id,
            wallet_address=admin_wallet_address,
            circle_wallet_id="admin_wallet",  # Placeholder for admin wallet
            created_at=datetime.utcnow()
        )
        db.add(user_wallet)
        db.commit()
        db.refresh(user)
        
        # Create JWT token
        access_token = create_access_token(
            data={"sub": user.id, "email": user.email, "role": user.role}
        )
        
        return LoginResponse(
            user_id=user.id,
            email=user.email,
            role=user.role,
            wallet_address=admin_wallet_address,
            access_token=access_token
        )
    
    # ADMIN_WALLET_ADDRESS not set - try to use existing insurer user
    # Find first insurer user with a wallet
    insurer_user = db.query(User).filter(User.role == "insurer").first()
    
    if not insurer_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No admin account found. Please either: (1) Set ADMIN_WALLET_ADDRESS environment variable, or (2) Create an insurer account first via registration."
        )
    
    # Get wallet for this user
    user_wallet = db.query(UserWallet).filter(UserWallet.user_id == insurer_user.id).first()
    
    if not user_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin user '{insurer_user.email}' found but has no wallet address. Please complete wallet setup first, or set ADMIN_WALLET_ADDRESS environment variable."
        )
    
    # Use existing admin user
    access_token = create_access_token(
        data={"sub": insurer_user.id, "email": insurer_user.email, "role": insurer_user.role}
    )
    
    return LoginResponse(
        user_id=insurer_user.id,
        email=insurer_user.email,
        role=insurer_user.role,
        wallet_address=user_wallet.wallet_address,
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
    circle_service: CircleWalletsService = Depends(get_circle_wallets_service)
):
    """
    Get current user's wallet information.
    
    For User-Controlled wallets, fetches wallet from Circle API using user ID.
    Returns wallet address, Circle wallet ID, and balance information.
    """
    user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
    
    # If no wallet in DB, try to fetch from Circle
    if not user_wallet:
        try:
            if circle_service.app_id:
                # Get wallets from Circle for this user
                wallets = await circle_service.get_user_wallets(current_user.id, blockchains=["ARC-TESTNET"])
                if wallets and len(wallets) > 0:
                    wallet = wallets[0]
                    # Store in DB for future reference
                    user_wallet = UserWallet(
                        user_id=current_user.id,
                        wallet_address=wallet.get("address") or wallet.get("walletAddress"),
                        circle_wallet_id=wallet.get("id") or wallet.get("walletId"),
                        wallet_set_id=wallet.get("walletSetId")
                    )
                    db.add(user_wallet)
                    db.commit()
        except Exception as e:
            import logging
            logging.warning(f"Failed to fetch wallet from Circle for user {current_user.id}: {e}")
    
    if not user_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found for user. Please create a wallet by logging in and completing the PIN challenge."
        )
    
    # Get wallet balance and blockchain info
    balance = None
    blockchain = "ARC-TESTNET"  # Default to ARC-TESTNET since we query for it
    
    try:
        # Try to fetch balance from Circle API if we have a wallet ID
        if user_wallet.circle_wallet_id and circle_service.api_key:
            import logging
            logging.info(f"Fetching balance for wallet {user_wallet.circle_wallet_id}")
            try:
                # Fetch balance from Circle API
                balance_data = await circle_service.get_wallet_balance(
                    user_wallet.circle_wallet_id,
                    chain="ARC"  # Circle API uses "ARC" for ARC-TESTNET
                )
                logging.info(f"Balance data received: {balance_data}")
                # Always return balance data, even if empty (so frontend knows we tried)
                balance = balance_data
            except Exception as e:
                import logging
                logging.error(f"Could not fetch balance from Circle: {e}", exc_info=True)
                # Return empty balance structure on error
                balance = {
                    "balances": [],
                    "wallet_id": user_wallet.circle_wallet_id
                }
    except Exception as e:
        import logging
        logging.error(f"Error in balance fetching logic: {e}", exc_info=True)
        # Balance fetch is optional, continue without it
    
    return WalletInfoResponse(
        wallet_address=user_wallet.wallet_address,
        circle_wallet_id=user_wallet.circle_wallet_id,
        wallet_set_id=user_wallet.wallet_set_id,
        blockchain=blockchain,
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


# ============================================================================
# Circle User-Controlled Wallet Connect (Web SDK)
# ============================================================================

class CircleConnectInitResponse(BaseModel):
    """Init payload for Circle Web SDK connect (user-controlled wallets)."""
    available: bool
    app_id: Optional[str] = None
    user_token: Optional[str] = None
    encryption_key: Optional[str] = None
    challenge_id: Optional[str] = None
    message: Optional[str] = None


class CircleConnectCompleteResponse(BaseModel):
    """Completion response after Circle connect finishes."""
    success: bool
    wallet_address: Optional[str] = None
    circle_wallet_id: Optional[str] = None


@router.post("/circle/connect/init", response_model=CircleConnectInitResponse)
async def circle_connect_init(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    circle_service: CircleWalletsService = Depends(get_circle_service),
):
    """
    Initialize Circle User-Controlled wallet connect for the Web SDK.

    Returns app_id + (user_token, encryption_key) + challenge_id for the SDK to execute.
    If Circle is not configured, returns available=false.
    """
    import logging
    
    # Log App ID for debugging (masked for security)
    app_id = circle_service.app_id
    if app_id:
        masked_id = f"{app_id[:8]}...{app_id[-4:]}" if len(app_id) > 12 else "***"
        logging.info(f"Using Circle App ID: {masked_id}")
    else:
        logging.warning("CIRCLE_APP_ID is not set")
    
    # Early validation: Check App ID before proceeding
    if not circle_service.validate_app_id():
        return CircleConnectInitResponse(
            available=False,
            message="Circle App ID is not configured. Please set CIRCLE_APP_ID in backend/.env"
        )
    
    # If Circle isn't configured, the service will raise; return a friendly payload instead.
    try:
        # Ensure Circle "user" exists (Circle userId is our user.id)
        # 409 is OK - means user already exists
        try:
            await circle_service.create_user(current_user.id)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                # User already exists - that's fine, continue
                import logging
                logging.info(f"Circle user already exists for {current_user.email}")
            else:
                raise  # Re-raise if it's a different error

        # Create a Web SDK session token (PIN flow) -> userToken + encryptionKey
        token_data = await circle_service.create_user_token(current_user.id)
        user_token = token_data.get("userToken")
        encryption_key = token_data.get("encryptionKey")

        if not user_token or not encryption_key:
            return CircleConnectInitResponse(
                available=False,
                message="Circle token issuance failed (missing session credentials).",
            )

        # Initialize user to get a challengeId
        # Use ARC-TESTNET (not ARC) for Circle API
        init_data = await circle_service.initialize_user(
            user_token,
            account_type="SCA",
            blockchains=["ARC-TESTNET"]
        )
        challenge_id = init_data.get("challengeId") or init_data.get("challenge_id")
        already_initialized = init_data.get("alreadyInitialized", False)
        
        import logging
        logging.info(f"Circle initialize_user response for user {current_user.id} ({current_user.email}): challenge_id={challenge_id}, already_initialized={already_initialized}")
        logging.info(f"Full init_data: {init_data}")

        # If we have a challenge_id, proceed with wallet creation (even if user is already initialized)
        # This allows users who were initialized but never completed wallet setup to create a wallet
        if challenge_id:
            logging.info(f"Challenge ID available for user {current_user.id}, proceeding with wallet creation flow")
            return CircleConnectInitResponse(
                available=True,
                app_id=circle_service.app_id or "",
                user_token=user_token,
                encryption_key=encryption_key,
                challenge_id=challenge_id,
            )

        # If no challenge_id and user is already initialized, check if they have a wallet
        if already_initialized:
            logging.info(f"User {current_user.id} ({current_user.email}) is already initialized but no challenge_id. Checking for existing wallet...")
            # User is already initialized - check if they have a wallet in our DB
            user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
            
            if user_wallet and user_wallet.wallet_address:
                # User already has a wallet - return success without challenge
                # Frontend will need to handle this case (skip SDK execute)
                return CircleConnectInitResponse(
                    available=True,
                    app_id=circle_service.app_id or "",
                    user_token=user_token,
                    encryption_key=encryption_key,
                    challenge_id=None,  # No challenge needed - user already has wallet
                    message="User already initialized with wallet. Wallet setup complete.",
                )
            
            # User is initialized but no wallet in DB - try to fetch from Circle
            # For User-Controlled wallets, use list_wallets with user_token (not get_user_wallets)
            try:
                logging.info(f"Attempting to fetch wallets from Circle for user {current_user.id} using user token (User-Controlled wallets endpoint)")
                wallets = await circle_service.list_wallets(user_token)
                logging.info(f"Found {len(wallets)} wallet(s) using user token endpoint")
                
                if wallets:
                    logging.info(f"Successfully found {len(wallets)} wallet(s) in Circle for user {current_user.id}")
                    for i, w in enumerate(wallets):
                        logging.info(f"  Wallet {i+1}: {w}")
                    # Found wallet in Circle - save it to DB
                    wallet = wallets[0]
                    wallet_id = wallet.get("walletId") or wallet.get("id") or wallet.get("wallet_id")
                    address = wallet.get("address")
                    
                    if wallet_id and address:
                        # Save wallet to DB
                        if not user_wallet:
                            user_wallet = UserWallet(
                                user_id=current_user.id,
                                wallet_address=address,
                                circle_wallet_id=wallet_id,
                                wallet_set_id=wallet.get("walletSetId") or wallet.get("wallet_set_id"),
                            )
                            db.add(user_wallet)
                        else:
                            user_wallet.wallet_address = address
                            user_wallet.circle_wallet_id = wallet_id
                            user_wallet.wallet_set_id = wallet.get("walletSetId") or wallet.get("wallet_set_id") or user_wallet.wallet_set_id
                        db.commit()
                        
                        # Return success - wallet already exists
                        return CircleConnectInitResponse(
                            available=True,
                            app_id=circle_service.app_id or "",
                            user_token=user_token,
                            encryption_key=encryption_key,
                            challenge_id=None,  # No challenge needed
                            message="User already initialized. Wallet retrieved and saved.",
                        )
            except Exception as e:
                import logging
                logging.error(f"Exception while fetching wallets from Circle for user {current_user.id}: {e}", exc_info=True)
                logging.error(f"Exception type: {type(e).__name__}")
                if hasattr(e, 'response'):
                    logging.error(f"HTTP response status: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}")
                    logging.error(f"HTTP response text: {getattr(e.response, 'text', 'N/A')}")
            
            # User is initialized but no wallet found - they need to complete setup
            # Log user_id for debugging in Circle portal
            logging.error(f"User {current_user.id} ({current_user.email}) is initialized in Circle but no wallet found.")
            logging.error(f"Please check Circle portal for user_id: {current_user.id}")
            logging.error(f"Circle user should exist but wallet creation may not have completed.")
            logging.error(f"Full init_data from Circle: {init_data}")
            
            return CircleConnectInitResponse(
                available=False,
                message=f"User is initialized but no wallet found. Please complete wallet setup via Circle Connect. (User ID: {current_user.id} - check Circle portal)",
            )
        
        # If no challenge_id and not already initialized, it's an error
        if not challenge_id:
            return CircleConnectInitResponse(
                available=False,
                message="Circle initialization failed (missing challengeId).",
            )

        return CircleConnectInitResponse(
            available=True,
            app_id=circle_service.app_id or "",
            user_token=user_token,
            encryption_key=encryption_key,
            challenge_id=challenge_id,
        )
    except httpx.HTTPStatusError as e:
        # Handle specific HTTP errors
        error_msg = ""
        if e.response.headers.get("content-type", "").startswith("application/json"):
            error_data = e.response.json()
            error_msg = error_data.get("message", error_data.get("detail", ""))
        
        if e.response.status_code == 400:
            error_lower = error_msg.lower()
            if "app" in error_lower and ("id" in error_lower or "not recognized" in error_lower):
                # App ID not recognized
                masked_app_id = f"{circle_service.app_id[:8]}...{circle_service.app_id[-4:]}" if circle_service.app_id and len(circle_service.app_id) > 12 else "N/A"
                logging.error(f"Circle App ID validation failed: {error_msg}")
                logging.error(f"App ID being used: {masked_app_id}")
                return CircleConnectInitResponse(
                    available=False,
                    message=f"Circle App ID is not recognized. Please verify CIRCLE_APP_ID in backend/.env matches your Circle Developer Console App ID. Error: {error_msg}",
                )
        
        if e.response.status_code == 409:
            # User already exists - try to continue anyway
            try:
                token_data = await circle_service.create_user_token(current_user.id)
                user_token = token_data.get("userToken")
                encryption_key = token_data.get("encryptionKey")
                if user_token and encryption_key:
                    init_data = await circle_service.initialize_user(
                        user_token,
                        account_type="SCA",
                        blockchains=["ARC-TESTNET"]
                    )
                    challenge_id = init_data.get("challengeId") or init_data.get("challenge_id")
                    if challenge_id:
                        return CircleConnectInitResponse(
                            available=True,
                            app_id=circle_service.app_id or "",
                            user_token=user_token,
                            encryption_key=encryption_key,
                            challenge_id=challenge_id,
                        )
            except Exception:
                pass  # Fall through to error response
        
        return CircleConnectInitResponse(
            available=False,
            message=f"Circle connect error (HTTP {e.response.status_code}): {error_msg or e.response.text[:200]}",
        )
    except Exception as e:
        import logging
        logging.exception("Circle connect init error")
        return CircleConnectInitResponse(
            available=False,
            message=f"Circle connect not available: {str(e)}",
        )


@router.post("/circle/connect/complete", response_model=CircleConnectCompleteResponse)
async def circle_connect_complete(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    circle_service: CircleWalletsService = Depends(get_circle_service),
):
    """
    After the Web SDK challenge succeeds, fetch the user's Circle wallet and persist mapping.
    """
    import logging
    logging.info(f"Checking for wallet for user {current_user.id} ({current_user.email})")
    
    try:
        # For User-Controlled wallets, we need to use list_wallets with user_token
        # First, create a user token
        logging.info(f"Creating user token for user {current_user.id} to query wallets")
        token_data = await circle_service.create_user_token(current_user.id)
        user_token = token_data.get("userToken")
        
        if not user_token:
            logging.error(f"Failed to create user token for user {current_user.id}")
            return CircleConnectCompleteResponse(
                success=False,
                wallet_address=None,
                circle_wallet_id=None
            )
        
        # Use list_wallets with user token (correct endpoint for User-Controlled wallets)
        logging.info(f"Querying Circle API for wallets using user token (User-Controlled wallets endpoint)")
        wallets = await circle_service.list_wallets(user_token)
        logging.info(f"Found {len(wallets)} wallet(s) using user token endpoint")

        if not wallets:
            # No wallets found - log this for debugging
            logging.warning(f"No wallets found in Circle API for user {current_user.id} ({current_user.email})")
            logging.warning(f"This could mean: (1) Wallet creation is still in progress, (2) User hasn't completed PIN challenge, or (3) Wallet was not created")
            
            # Check if user has a wallet in our DB (might be stale)
            user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
            if user_wallet:
                logging.warning(f"User has wallet in DB but not in Circle: wallet_id={user_wallet.circle_wallet_id}, address={user_wallet.wallet_address}")
            
            return CircleConnectCompleteResponse(
                success=False,
                wallet_address=None,
                circle_wallet_id=None
            )

        wallet = wallets[0]
        wallet_id = wallet.get("walletId") or wallet.get("id") or wallet.get("wallet_id")
        address = wallet.get("address")
        
        logging.info(f"Found wallet in Circle: wallet_id={wallet_id}, address={address}")
        logging.info(f"Full wallet data: {wallet}")

        if not wallet_id or not address:
            logging.error(f"Malformed wallet payload from Circle: {wallet}")
            raise HTTPException(status_code=500, detail="Malformed Circle wallet payload")

        # Upsert user_wallet mapping
        user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
        if user_wallet:
            user_wallet.wallet_address = address
            user_wallet.circle_wallet_id = wallet_id
            user_wallet.wallet_set_id = wallet.get("walletSetId") or wallet.get("wallet_set_id") or user_wallet.wallet_set_id
        else:
            user_wallet = UserWallet(
                user_id=current_user.id,
                wallet_address=address,
                circle_wallet_id=wallet_id,
                wallet_set_id=wallet.get("walletSetId") or wallet.get("wallet_set_id"),
            )
            db.add(user_wallet)

        db.commit()

        return CircleConnectCompleteResponse(success=True, wallet_address=address, circle_wallet_id=wallet_id)
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        # Handle HTTP errors gracefully
        if e.response.status_code == 404:
            # 404 means no wallets found - expected if user hasn't completed PIN challenge
            return CircleConnectCompleteResponse(
                success=False,
                wallet_address=None,
                circle_wallet_id=None
            )
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to complete Circle connect: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to complete Circle connect: {str(e)}")


@router.get("/circle/connect/status", response_model=Dict[str, Any])
async def circle_connect_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    circle_service: CircleWalletsService = Depends(get_circle_service),
):
    """
    Diagnostic endpoint to check wallet status in Circle and local database.
    Useful for debugging wallet availability issues.
    """
    import logging
    
    status = {
        "user_id": current_user.id,
        "user_email": current_user.email,
        "circle_wallets": [],
        "db_wallet": None,
        "has_circle_wallet": False,
        "has_db_wallet": False,
    }
    
    try:
        # Check Circle API for wallets using User-Controlled wallets endpoint
        logging.info(f"Checking Circle API for wallets for user {current_user.id}")
        
        # Create user token for User-Controlled wallets endpoint
        token_data = await circle_service.create_user_token(current_user.id)
        user_token = token_data.get("userToken")
        
        if user_token:
            # Use list_wallets (correct endpoint for User-Controlled wallets)
            wallets_all = await circle_service.list_wallets(user_token)
            wallets_arc = [w for w in wallets_all if w.get("blockchain") in ["ARC-TESTNET", "ARC", "ARBITRUM"]]
        else:
            logging.warning(f"Could not create user token for status check, falling back to get_user_wallets")
            wallets_arc = await circle_service.get_user_wallets(current_user.id, blockchains=["ARC-TESTNET"])
            wallets_all = await circle_service.get_user_wallets(current_user.id, blockchains=None)
        
        # Use all wallets (from both queries, deduplicated)
        all_wallets = wallets_arc if wallets_arc else wallets_all
        if wallets_arc and wallets_all and wallets_arc != wallets_all:
            # Merge if different
            all_wallets = wallets_arc + [w for w in wallets_all if w not in wallets_arc]
        
        status["circle_wallets"] = all_wallets
        status["has_circle_wallet"] = len(all_wallets) > 0
        
        if all_wallets:
            logging.info(f"Found {len(all_wallets)} wallet(s) in Circle for user {current_user.id}")
            for wallet in all_wallets:
                wallet_id = wallet.get("walletId") or wallet.get("id") or wallet.get("wallet_id")
                address = wallet.get("address")
                logging.info(f"  - Wallet ID: {wallet_id}, Address: {address}")
        else:
            logging.warning(f"No wallets found in Circle API for user {current_user.id}")
        
        # Check local database
        user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
        if user_wallet:
            status["db_wallet"] = {
                "wallet_address": user_wallet.wallet_address,
                "circle_wallet_id": user_wallet.circle_wallet_id,
                "wallet_set_id": user_wallet.wallet_set_id,
            }
            status["has_db_wallet"] = True
            logging.info(f"Found wallet in DB: {user_wallet.wallet_address} (Circle ID: {user_wallet.circle_wallet_id})")
        else:
            logging.info(f"No wallet found in local database for user {current_user.id}")
        
        # Check if there's a mismatch
        if status["has_circle_wallet"] and status["has_db_wallet"]:
            circle_addresses = [w.get("address") for w in all_wallets if w.get("address")]
            if user_wallet.wallet_address not in circle_addresses:
                status["mismatch"] = True
                status["mismatch_details"] = f"DB wallet {user_wallet.wallet_address} not found in Circle wallets"
                logging.warning(f"Wallet mismatch: DB has {user_wallet.wallet_address} but Circle has {circle_addresses}")
            else:
                status["mismatch"] = False
        elif status["has_circle_wallet"] and not status["has_db_wallet"]:
            status["mismatch"] = True
            status["mismatch_details"] = "Wallet exists in Circle but not in local database"
            logging.warning(f"Wallet exists in Circle but not in DB for user {current_user.id}")
        elif not status["has_circle_wallet"] and status["has_db_wallet"]:
            status["mismatch"] = True
            status["mismatch_details"] = "Wallet exists in local database but not in Circle"
            logging.warning(f"Wallet exists in DB but not in Circle for user {current_user.id}")
        
    except Exception as e:
        import logging
        logging.error(f"Error checking wallet status: {e}", exc_info=True)
        status["error"] = str(e)
    
    return status


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
