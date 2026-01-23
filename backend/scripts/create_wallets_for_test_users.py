#!/usr/bin/env python3
"""
Create Circle Wallets for Test Users

This script programmatically creates Circle wallets for test users.
For User-Controlled wallets, this simulates the frontend SDK flow.

Usage:
    python backend/scripts/create_wallets_for_test_users.py
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
from src.services.circle_wallets import CircleWalletsService
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")


def print_success(text: str):
    """Print a success message."""
    print(f"{Colors.OKGREEN}  ✅ {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print a warning message."""
    print(f"{Colors.WARNING}  ⚠️  {text}{Colors.ENDC}")


def print_error(text: str):
    """Print an error message."""
    print(f"{Colors.FAIL}  ❌ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print an info message."""
    print(f"{Colors.OKBLUE}  ℹ️  {text}{Colors.ENDC}")


async def create_wallet_for_user(email: str, circle_service: CircleWalletsService) -> bool:
    """Create a Circle wallet for a user."""
    db = SessionLocal()
    
    try:
        # Find user in database
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print_error(f"User {email} not found in database")
            return False
        
        print_info(f"Creating wallet for {email} (user_id: {user.id})")
        
        # Step 1: Ensure Circle user exists
        try:
            circle_user = await circle_service.create_user(user.id)
            print_success(f"Circle user ready: {circle_user.get('id', user.id)}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                print_info("Circle user already exists (409)")
            else:
                print_error(f"Failed to create Circle user: {e.response.status_code}")
                return False
        
        # Step 2: Get user token
        try:
            token_data = await circle_service.create_user_token(user.id)
            user_token = token_data.get("userToken")
            encryption_key = token_data.get("encryptionKey")
            
            if not user_token:
                print_error("Failed to get user token")
                return False
            
            print_success("User token retrieved")
        except Exception as e:
            print_error(f"Failed to get user token: {e}")
            return False
        
        # Step 3: Check if wallet already exists
        try:
            existing_wallets = await circle_service.get_user_wallets(user.id, blockchains=["ARC-TESTNET"])
            if existing_wallets and len(existing_wallets) > 0:
                wallet = existing_wallets[0]
                wallet_id = wallet.get("id") or wallet.get("walletId")
                wallet_address = wallet.get("address")
                
                print_info(f"Wallet already exists: {wallet_address}")
                
                # Update database
                user_wallet = db.query(UserWallet).filter(UserWallet.user_id == user.id).first()
                if user_wallet:
                    user_wallet.wallet_address = wallet_address
                    user_wallet.circle_wallet_id = wallet_id
                    user_wallet.wallet_set_id = wallet.get("walletSetId")
                else:
                    user_wallet = UserWallet(
                        user_id=user.id,
                        wallet_address=wallet_address,
                        circle_wallet_id=wallet_id,
                        wallet_set_id=wallet.get("walletSetId")
                    )
                    db.add(user_wallet)
                
                db.commit()
                print_success(f"Wallet info updated in database: {wallet_address}")
                return True
        except Exception as e:
            print_warning(f"Could not check existing wallets: {e}")
        
        # Step 4: Create wallet using Circle API
        # For User-Controlled wallets, we need to use the create_wallet endpoint
        try:
            wallet_data = await circle_service.create_wallet(
                user_id=user.id,
                blockchains=["ARC-TESTNET"]
            )
            
            wallet_id = wallet_data.get("id") or wallet_data.get("walletId")
            wallet_address = wallet_data.get("address")
            
            if not wallet_id or not wallet_address:
                print_error("Invalid wallet data returned")
                return False
            
            print_success(f"Wallet created: {wallet_address}")
            
            # Step 5: Store in database
            user_wallet = db.query(UserWallet).filter(UserWallet.user_id == user.id).first()
            if user_wallet:
                user_wallet.wallet_address = wallet_address
                user_wallet.circle_wallet_id = wallet_id
                user_wallet.wallet_set_id = wallet_data.get("walletSetId")
            else:
                user_wallet = UserWallet(
                    user_id=user.id,
                    wallet_address=wallet_address,
                    circle_wallet_id=wallet_id,
                    wallet_set_id=wallet_data.get("walletSetId")
                )
                db.add(user_wallet)
            
            db.commit()
            print_success(f"Wallet stored in database: {wallet_address}")
            return True
            
        except httpx.HTTPStatusError as e:
            error_msg = f"Failed to create wallet: HTTP {e.response.status_code}"
            if e.response.headers.get("content-type", "").startswith("application/json"):
                error_data = e.response.json()
                error_msg += f" - {error_data.get('message', e.response.text[:200])}"
            print_error(error_msg)
            
            # If wallet creation fails, it might be because we need to initialize first
            if e.response.status_code == 400:
                print_info("Wallet creation failed - user may need to complete initialization via frontend")
                print_info("For demo: Users need to log in via frontend and complete PIN challenge")
            
            return False
        except Exception as e:
            print_error(f"Failed to create wallet: {e}")
            return False
        
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def main():
    """Main function to create wallets for all test users."""
    print_header("Create Circle Wallets for Test Users")
    
    # Check environment
    api_key = os.getenv("CIRCLE_WALLETS_API_KEY")
    app_id = os.getenv("CIRCLE_APP_ID")
    
    if not api_key:
        print_error("CIRCLE_WALLETS_API_KEY not set")
        print_info("Set it in backend/.env or as environment variable")
        return 1
    
    if not app_id:
        print_warning("CIRCLE_APP_ID not set - User-Controlled wallets require this")
        print_info("Continuing anyway...")
    
    # Test users
    test_users = [
        "admin@uclaim.com",
        "claimant@uclaim.com",
        "claimant1@uclaim.com",
        "claimant2@uclaim.com"
    ]
    
    circle_service = CircleWalletsService()
    results = {}
    
    try:
        for email in test_users:
            print(f"\n{Colors.OKCYAN}{'─'*70}{Colors.ENDC}")
            success = await create_wallet_for_user(email, circle_service)
            results[email] = success
        
        # Summary
        print_header("Summary")
        
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        print_info(f"Total users: {total}")
        print_success(f"Wallets created/verified: {successful}")
        
        if successful < total:
            print_warning(f"Failed: {total - successful}")
            print_info("\nNote: Some wallets may require frontend PIN challenge completion")
            print_info("For demo: Users can log in via frontend to complete wallet setup")
        
        print("\nDetailed Results:")
        for email, success in results.items():
            status = "✅" if success else "❌"
            print(f"  {status} {email}")
        
        if successful == total:
            print_success("\n✅ All wallets ready for demo!")
            return 0
        else:
            print_warning(f"\n⚠️  {total - successful} wallets need frontend setup")
            return 1
    
    except Exception as e:
        print_error(f"Script failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await circle_service.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
