#!/usr/bin/env python3
"""
Verify Demo User Wallets

This script:
1. Creates/verifies demo users exist in local DB
2. Creates Circle user accounts
3. Gets user tokens
4. Initializes users (which may create wallets)
5. Lists wallets from Circle API
6. Cross-checks wallet addresses with database
7. Updates database if needed

Usage:
    python backend/scripts/verify_demo_user_wallets.py
"""

import os
import sys
import asyncio
import httpx
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

from src.database import SessionLocal
from src.models import User, UserWallet
from src.services.auth import get_password_hash
from src.services.circle_wallets import CircleWalletsService
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_demo_user(email: str, password: str, role: str, circle_service: CircleWalletsService):
    """Verify a demo user and their wallet."""
    db = SessionLocal()
    
    try:
        print(f"\n{'='*60}")
        print(f"Verifying {email} ({role})")
        print(f"{'='*60}")
        
        # Step 1: Check if user exists in local DB
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"  ❌ User {email} not found in local database")
            print(f"  Creating user...")
            user = User(
                id=str(uuid.uuid4()),
                email=email,
                password_hash=get_password_hash(password),
                role=role
            )
            db.add(user)
            db.flush()
            print(f"  ✅ Created local user: {user.id}")
        else:
            print(f"  ✅ User exists in local DB: {user.id}")
        
        # Step 2: Create Circle user (createUser)
        print(f"\n  Step 1: Creating Circle user...")
        try:
            circle_user = await circle_service.create_user(user.id)
            circle_user_id = circle_user.get('id', 'N/A')
            print(f"  ✅ Circle user created/retrieved: {circle_user_id}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                print(f"  ℹ️  Circle user already exists (409)")
                # Try to get user info
                circle_user_id = user.id
            else:
                print(f"  ❌ Failed to create Circle user: {e.response.status_code}")
                print(f"     Response: {e.response.text}")
                return
        except Exception as e:
            print(f"  ❌ Error creating Circle user: {e}")
            return
        
        # Step 3: Get user token (getUserToken)
        print(f"\n  Step 2: Getting user token...")
        try:
            token_data = await circle_service.create_user_token(user.id)
            user_token = token_data.get("userToken")
            encryption_key = token_data.get("encryptionKey")
            
            if user_token and encryption_key:
                print(f"  ✅ User token retrieved")
                print(f"     userToken: {user_token[:20]}...")
                print(f"     encryptionKey: {encryption_key[:20]}...")
            else:
                print(f"  ⚠️  Missing userToken or encryptionKey")
                return
        except Exception as e:
            print(f"  ❌ Failed to get user token: {e}")
            return
        
        # Step 4: Initialize user (initializeUser)
        print(f"\n  Step 3: Initializing user...")
        try:
            init_data = await circle_service.initialize_user(
                user_token,
                account_type="SCA",
                blockchains=["ARC-TESTNET"]
            )
            challenge_id = init_data.get("challengeId") or init_data.get("challenge_id")
            
            if challenge_id:
                print(f"  ✅ User initialized")
                print(f"     challengeId: {challenge_id[:30]}...")
                print(f"     Note: Wallet will be created when challenge is executed via frontend SDK")
            else:
                print(f"  ⚠️  No challengeId returned (user may already be initialized)")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                error_data = e.response.json() if e.response.headers.get("content-type", "").startswith("application/json") else {}
                error_code = error_data.get("code")
                if error_code == 155106:  # User already initialized
                    print(f"  ℹ️  User already initialized (code 155106)")
                else:
                    print(f"  ⚠️  Initialization returned 400: {error_data.get('message', e.response.text)}")
            else:
                print(f"  ⚠️  Initialization failed: {e.response.status_code}")
                print(f"     Response: {e.response.text}")
        except Exception as e:
            print(f"  ⚠️  Error initializing user: {e}")
        
        # Step 5: List wallets (listWallets) - using user token
        print(f"\n  Step 4: Listing wallets from Circle...")
        try:
            # Try using user token first (preferred for User-Controlled wallets)
            try:
                wallets = await circle_service.list_wallets(user_token)
            except Exception:
                # Fallback to user ID method
                wallets = await circle_service.get_user_wallets(user.id, blockchains=["ARC"])
            
            if wallets and len(wallets) > 0:
                print(f"  ✅ Found {len(wallets)} wallet(s)")
                for i, wallet in enumerate(wallets):
                    wallet_id = wallet.get("id") or wallet.get("walletId")
                    wallet_address = wallet.get("address") or wallet.get("walletAddress")
                    blockchain = wallet.get("blockchain", "ARC")
                    
                    print(f"\n     Wallet {i+1}:")
                    print(f"       ID: {wallet_id}")
                    print(f"       Address: {wallet_address}")
                    print(f"       Blockchain: {blockchain}")
                    
                    # Step 6: Cross-check with database
                    print(f"\n  Step 5: Cross-checking with database...")
                    db_wallet = db.query(UserWallet).filter(UserWallet.user_id == user.id).first()
                    
                    if db_wallet:
                        if db_wallet.wallet_address == wallet_address:
                            print(f"  ✅ Wallet address matches database!")
                            print(f"     DB: {db_wallet.wallet_address}")
                            print(f"     Circle: {wallet_address}")
                        else:
                            print(f"  ⚠️  Wallet address mismatch!")
                            print(f"     DB: {db_wallet.wallet_address}")
                            print(f"     Circle: {wallet_address}")
                            print(f"     Updating database...")
                            db_wallet.wallet_address = wallet_address
                            db_wallet.circle_wallet_id = wallet_id
                            db.commit()
                            print(f"  ✅ Database updated")
                    else:
                        print(f"  ℹ️  No wallet in database, creating entry...")
                        db_wallet = UserWallet(
                            user_id=user.id,
                            wallet_address=wallet_address,
                            circle_wallet_id=wallet_id,
                            wallet_set_id=wallet.get("walletSetId")
                        )
                        db.add(db_wallet)
                        db.commit()
                        print(f"  ✅ Wallet entry created in database")
            else:
                print(f"  ℹ️  No wallets found for user")
                print(f"     Wallet will be created when user logs in and completes PIN challenge")
                
                # Check if there's a stale wallet entry in DB
                db_wallet = db.query(UserWallet).filter(UserWallet.user_id == user.id).first()
                if db_wallet:
                    print(f"  ⚠️  Found wallet entry in DB but no wallet in Circle:")
                    print(f"     DB wallet: {db_wallet.wallet_address}")
                    print(f"     This may be a placeholder or stale entry")
        except Exception as e:
            print(f"  ❌ Failed to list wallets: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n  ✅ Verification complete for {email}")
        
    except Exception as e:
        print(f"  ❌ Error verifying user: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def main():
    """Main function to verify all demo users."""
    print("="*60)
    print("DEMO USER WALLET VERIFICATION")
    print("="*60)
    print()
    
    # Check Circle credentials
    api_key = os.getenv("CIRCLE_WALLETS_API_KEY")
    app_id = os.getenv("CIRCLE_APP_ID")
    
    if not api_key:
        print("❌ ERROR: CIRCLE_WALLETS_API_KEY not set")
        print("   Set it in backend/.env or as environment variable")
        return
    
    if not app_id:
        print("⚠️  WARNING: CIRCLE_APP_ID not set")
        print("   User-Controlled wallets require CIRCLE_APP_ID")
        print("   Continuing anyway...")
    
    # Initialize Circle service
    circle_service = CircleWalletsService()
    
    # Demo users
    demo_users = [
        {
            "email": "admin@uclaim.com",
            "password": "AdminDemo123!",
            "role": "insurer"
        },
        {
            "email": "claimant@uclaim.com",
            "password": "ClaimantDemo123!",
            "role": "claimant"
        }
    ]
    
    # Verify each user
    for user_info in demo_users:
        await verify_demo_user(
            user_info["email"],
            user_info["password"],
            user_info["role"],
            circle_service
        )
    
    # Close service
    await circle_service.close()
    
    print(f"\n{'='*60}")
    print("VERIFICATION COMPLETE")
    print(f"{'='*60}")
    print("\nSummary:")
    print("- Demo users created/verified in local database")
    print("- Circle user accounts created/verified")
    print("- Wallet addresses cross-checked between Circle API and database")
    print("\nNote: If wallets don't exist yet, they will be created when users")
    print("      log in and complete the PIN challenge via the frontend SDK.")


if __name__ == "__main__":
    asyncio.run(main())
