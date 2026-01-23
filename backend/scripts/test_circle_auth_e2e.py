#!/usr/bin/env python3
"""
End-to-End Test for Circle User-Backed Authentication Flow

This script tests the complete authentication flow for:
1. Demo users (admin and claimant)
2. 2 additional claimant users

Flow tested:
1. Register user (creates local user + Circle user account)
2. Login (gets JWT token)
3. Initialize Circle connect (gets userToken, encryptionKey, challengeId)
4. Complete Circle connect (fetches wallet from Circle and stores in DB)
5. Get wallet info
6. Get current user info

Usage:
    python backend/scripts/test_circle_auth_e2e.py
"""

import os
import sys
import asyncio
import httpx
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Optional
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

from src.database import SessionLocal
from src.models import User, UserWallet
from src.services.auth import get_password_hash
from src.services.circle_wallets import CircleWalletsService
import uuid
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
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")


def print_step(step_num: int, text: str):
    """Print a formatted step."""
    print(f"{Colors.OKCYAN}{Colors.BOLD}Step {step_num}:{Colors.ENDC} {text}")


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


class AuthFlowTester:
    """Test the complete Circle user-backed authentication flow."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.circle_service = CircleWalletsService()
        self.results: Dict[str, Any] = {}
    
    async def close(self):
        """Close HTTP clients."""
        await self.http_client.aclose()
        await self.circle_service.close()
    
    async def test_user_flow(self, email: str, password: str, role: str) -> Dict[str, Any]:
        """Test the complete authentication flow for a single user."""
        print_header(f"Testing User: {email} ({role})")
        
        result = {
            "email": email,
            "role": role,
            "steps": {},
            "success": False,
            "errors": []
        }
        
        try:
            # Step 1: Register user (or login if already exists)
            print_step(1, "Register/Login user")
            register_result = await self._register_user(email, password, role)
            result["steps"]["register"] = register_result
            
            if not register_result["success"]:
                # If user already exists, try to login instead
                if register_result.get("already_exists"):
                    print_info("User already exists, attempting login...")
                    login_result = await self._login_user(email, password)
                    if login_result["success"]:
                        register_result = login_result  # Use login result as register result
                        result["steps"]["register"] = register_result
                        print_success(f"User logged in: {login_result['user_id']}")
                    else:
                        result["errors"].append(f"Registration and login failed: {login_result.get('error')}")
                        return result
                else:
                    result["errors"].append(f"Registration failed: {register_result.get('error')}")
                    return result
            
            user_id = register_result["user_id"]
            access_token = register_result["access_token"]
            if register_result.get("already_exists"):
                print_success(f"User logged in: {user_id}")
            else:
                print_success(f"User registered: {user_id}")
            print_info(f"Access token: {access_token[:30]}...")
            
            # Step 2: Login
            print_step(2, "Login user")
            login_result = await self._login_user(email, password)
            result["steps"]["login"] = login_result
            
            if not login_result["success"]:
                result["errors"].append(f"Login failed: {login_result.get('error')}")
                return result
            
            login_token = login_result["access_token"]
            print_success("Login successful")
            print_info(f"Login token: {login_token[:30]}...")
            
            # Step 3: Get current user info
            print_step(3, "Get current user info")
            user_info_result = await self._get_current_user(login_token)
            result["steps"]["get_user_info"] = user_info_result
            
            if not user_info_result["success"]:
                result["errors"].append(f"Get user info failed: {user_info_result.get('error')}")
            else:
                print_success(f"User info retrieved: {user_info_result['email']} ({user_info_result['role']})")
            
            # Step 4: Initialize Circle connect
            print_step(4, "Initialize Circle connect")
            init_result = await self._init_circle_connect(login_token)
            result["steps"]["circle_init"] = init_result
            
            if not init_result["success"]:
                result["errors"].append(f"Circle init failed: {init_result.get('error')}")
                print_warning("Circle connect not available - this is OK if Circle is not configured")
            else:
                print_success("Circle connect initialized")
                print_info(f"App ID: {init_result.get('app_id', 'N/A')}")
                print_info(f"Challenge ID: {init_result.get('challenge_id', 'N/A')[:30]}...")
            
            # Step 5: Complete Circle connect (if init was successful)
            if init_result["success"]:
                print_step(5, "Complete Circle connect")
                complete_result = await self._complete_circle_connect(login_token)
                result["steps"]["circle_complete"] = complete_result
                
                if not complete_result["success"]:
                    result["errors"].append(f"Circle complete failed: {complete_result.get('error')}")
                    print_warning("Circle connect completion failed - wallet may not exist yet")
                    print_info("This is expected if the user hasn't completed the PIN challenge via frontend")
                else:
                    print_success("Circle connect completed")
                    print_info(f"Wallet address: {complete_result.get('wallet_address', 'N/A')}")
                    print_info(f"Circle wallet ID: {complete_result.get('circle_wallet_id', 'N/A')}")
            else:
                print_info("Skipping Circle connect complete (init failed)")
                result["steps"]["circle_complete"] = {"success": False, "skipped": True}
            
            # Step 6: Get wallet info
            print_step(6, "Get wallet info")
            wallet_result = await self._get_wallet_info(login_token)
            result["steps"]["get_wallet"] = wallet_result
            
            if not wallet_result["success"]:
                result["errors"].append(f"Get wallet failed: {wallet_result.get('error')}")
                print_warning("Wallet not found - this is OK if wallet hasn't been created yet")
            else:
                print_success("Wallet info retrieved")
                print_info(f"Wallet address: {wallet_result.get('wallet_address', 'N/A')}")
                print_info(f"Circle wallet ID: {wallet_result.get('circle_wallet_id', 'N/A')}")
            
            # Determine overall success
            critical_steps = ["register", "login", "get_user_info"]
            critical_success = all(
                result["steps"].get(step, {}).get("success", False)
                for step in critical_steps
            )
            
            result["success"] = critical_success
            
            if result["success"]:
                print_success(f"✅ Flow completed successfully for {email}")
            else:
                print_error(f"❌ Flow had errors for {email}")
                for error in result["errors"]:
                    print_error(f"  - {error}")
            
        except Exception as e:
            result["success"] = False
            result["errors"].append(f"Unexpected error: {str(e)}")
            print_error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        
        return result
    
    async def _register_user(self, email: str, password: str, role: str) -> Dict[str, Any]:
        """Register a new user."""
        try:
            response = await self.http_client.post(
                f"{self.base_url}/auth/register",
                json={
                    "email": email,
                    "password": password,
                    "role": role
                }
            )
            
            if response.status_code == 201:
                data = response.json()
                return {
                    "success": True,
                    "user_id": data.get("user_id"),
                    "email": data.get("email"),
                    "role": data.get("role"),
                    "access_token": data.get("access_token"),
                    "wallet_address": data.get("wallet_address")
                }
            elif response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get("detail", "Registration failed")
                if "already registered" in error_msg.lower():
                    print_warning("User already exists, will try login instead")
                    return {
                        "success": False,
                        "error": "User already exists",
                        "already_exists": True
                    }
                return {
                    "success": False,
                    "error": error_msg
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Login a user."""
        try:
            response = await self.http_client.post(
                f"{self.base_url}/auth/login",
                json={
                    "email": email,
                    "password": password
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "user_id": data.get("user_id"),
                    "email": data.get("email"),
                    "role": data.get("role"),
                    "access_token": data.get("access_token"),
                    "wallet_address": data.get("wallet_address")
                }
            else:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                return {
                    "success": False,
                    "error": error_data.get("detail", f"HTTP {response.status_code}: {response.text}")
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_current_user(self, token: str) -> Dict[str, Any]:
        """Get current user information."""
        try:
            response = await self.http_client.get(
                f"{self.base_url}/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "user_id": data.get("user_id"),
                    "email": data.get("email"),
                    "role": data.get("role"),
                    "wallet_address": data.get("wallet_address")
                }
            else:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                return {
                    "success": False,
                    "error": error_data.get("detail", f"HTTP {response.status_code}: {response.text}")
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _init_circle_connect(self, token: str) -> Dict[str, Any]:
        """Initialize Circle connect."""
        try:
            response = await self.http_client.post(
                f"{self.base_url}/auth/circle/connect/init",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("available"):
                    return {
                        "success": True,
                        "app_id": data.get("app_id"),
                        "user_token": data.get("user_token"),
                        "encryption_key": data.get("encryption_key"),
                        "challenge_id": data.get("challenge_id")
                    }
                else:
                    return {
                        "success": False,
                        "error": data.get("message", "Circle connect not available")
                    }
            else:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                return {
                    "success": False,
                    "error": error_data.get("detail", f"HTTP {response.status_code}: {response.text}")
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _complete_circle_connect(self, token: str) -> Dict[str, Any]:
        """Complete Circle connect."""
        try:
            response = await self.http_client.post(
                f"{self.base_url}/auth/circle/connect/complete",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return {
                        "success": True,
                        "wallet_address": data.get("wallet_address"),
                        "circle_wallet_id": data.get("circle_wallet_id")
                    }
                else:
                    return {
                        "success": False,
                        "error": "Circle connect completion returned success=false"
                    }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error": "No Circle wallets found for user (wallet not created yet)"
                }
            else:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                return {
                    "success": False,
                    "error": error_data.get("detail", f"HTTP {response.status_code}: {response.text}")
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_wallet_info(self, token: str) -> Dict[str, Any]:
        """Get wallet information."""
        try:
            response = await self.http_client.get(
                f"{self.base_url}/auth/wallet",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "wallet_address": data.get("wallet_address"),
                    "circle_wallet_id": data.get("circle_wallet_id"),
                    "wallet_set_id": data.get("wallet_set_id"),
                    "blockchain": data.get("blockchain"),
                    "balance": data.get("balance")
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error": "Wallet not found (wallet not created yet)"
                }
            else:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                return {
                    "success": False,
                    "error": error_data.get("detail", f"HTTP {response.status_code}: {response.text}")
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


async def create_wallets_for_users(base_url: str, test_users: list):
    """Create wallets for test users before running the test."""
    print_header("Creating Wallets for Test Users")
    print_info("This step creates Circle wallets programmatically for testing")
    
    try:
        # Import wallet creation function directly
        import sys
        from pathlib import Path
        wallet_script_path = Path(__file__).parent / "create_wallets_for_test_users.py"
        
        # Use the CircleWalletsService directly
        from src.services.circle_wallets import CircleWalletsService
        from src.database import SessionLocal
        from src.models import User, UserWallet
        
        circle_service = CircleWalletsService()
        wallet_results = {}
        db = SessionLocal()
        
        try:
            for user_info in test_users:
                email = user_info["email"]
                print(f"\n{Colors.OKCYAN}Creating wallet for {email}...{Colors.ENDC}")
                
                # Find user
                user = db.query(User).filter(User.email == email).first()
                if not user:
                    print_error(f"User {email} not found")
                    wallet_results[email] = False
                    continue
                
                # Create Circle user
                try:
                    await circle_service.create_user(user.id)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code != 409:
                        print_error(f"Failed to create Circle user: {e.response.status_code}")
                        wallet_results[email] = False
                        continue
                
                # Try to create wallet
                try:
                    wallet_data = await circle_service.create_wallet(
                        user_id=user.id,
                        blockchains=["ARC-TESTNET"]
                    )
                    
                    wallet_id = wallet_data.get("id") or wallet_data.get("walletId")
                    wallet_address = wallet_data.get("address")
                    
                    if wallet_id and wallet_address:
                        # Store in database
                        user_wallet = db.query(UserWallet).filter(UserWallet.user_id == user.id).first()
                        if user_wallet:
                            user_wallet.wallet_address = wallet_address
                            user_wallet.circle_wallet_id = wallet_id
                        else:
                            user_wallet = UserWallet(
                                user_id=user.id,
                                wallet_address=wallet_address,
                                circle_wallet_id=wallet_id
                            )
                            db.add(user_wallet)
                        db.commit()
                        print_success(f"Wallet created: {wallet_address}")
                        wallet_results[email] = True
                    else:
                        print_error("Invalid wallet data")
                        wallet_results[email] = False
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        print_warning("Wallet creation requires frontend PIN challenge")
                        wallet_results[email] = False
                    else:
                        print_error(f"Failed to create wallet: {e.response.status_code}")
                        wallet_results[email] = False
                except Exception as e:
                    print_error(f"Error creating wallet: {e}")
                    wallet_results[email] = False
        finally:
            db.close()
            await circle_service.close()
        
        successful = sum(1 for success in wallet_results.values() if success)
        total = len(wallet_results)
        
        if successful == total:
            print_success(f"✅ All {total} wallets created successfully!")
        else:
            print_warning(f"⚠️  {successful}/{total} wallets created")
            print_info("Some wallets may need frontend PIN challenge completion")
        
        return wallet_results
    except Exception as e:
        print_error(f"Wallet creation failed: {e}")
        print_info("Continuing with test - wallets may be created via frontend")
        import traceback
        traceback.print_exc()
        return {}


async def main():
    """Main function to test all users."""
    print_header("Circle User-Backed Authentication E2E Test")
    
    # Check environment
    api_key = os.getenv("CIRCLE_WALLETS_API_KEY")
    app_id = os.getenv("CIRCLE_APP_ID")
    
    print_info("Environment Check:")
    if api_key:
        print_success("CIRCLE_WALLETS_API_KEY is set")
    else:
        print_warning("CIRCLE_WALLETS_API_KEY not set - Circle features will be limited")
    
    if app_id:
        print_success("CIRCLE_APP_ID is set")
    else:
        print_warning("CIRCLE_APP_ID not set - User-Controlled wallets require this")
    
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    print_info(f"Testing against: {base_url}")
    
    # Test users
    test_users = [
        {
            "email": "admin@uclaim.com",
            "password": "AdminDemo123!",
            "role": "insurer"
        },
        {
            "email": "claimant@uclaim.com",
            "password": "ClaimantDemo123!",
            "role": "claimant"
        },
        {
            "email": "claimant1@uclaim.com",
            "password": "Claimant1Demo123!",
            "role": "claimant"
        },
        {
            "email": "claimant2@uclaim.com",
            "password": "Claimant2Demo123!",
            "role": "claimant"
        }
    ]
    
    # Step 1: Create wallets for all users (if Circle is configured)
    if api_key and app_id:
        wallet_results = await create_wallets_for_users(base_url, test_users)
    else:
        print_warning("Skipping wallet creation - Circle credentials not fully configured")
        wallet_results = {}
    
    # Step 2: Run authentication flow tests
    tester = AuthFlowTester(base_url=base_url)
    all_results = []
    
    try:
        # Test each user
        for user_info in test_users:
            result = await tester.test_user_flow(
                user_info["email"],
                user_info["password"],
                user_info["role"]
            )
            all_results.append(result)
        
        # Print summary
        print_header("Test Summary")
        
        total_users = len(all_results)
        successful_users = sum(1 for r in all_results if r["success"])
        failed_users = total_users - successful_users
        
        print_info(f"Total users tested: {total_users}")
        print_success(f"Successful flows: {successful_users}")
        if failed_users > 0:
            print_error(f"Failed flows: {failed_users}")
        
        print("\nDetailed Results:")
        for result in all_results:
            status = "✅" if result["success"] else "❌"
            print(f"\n{status} {result['email']} ({result['role']})")
            
            # Show step results
            for step_name, step_result in result["steps"].items():
                step_status = "✅" if step_result.get("success") else "❌"
                if step_result.get("skipped"):
                    step_status = "⏭️"
                print(f"   {step_status} {step_name}")
            
            if result["errors"]:
                for error in result["errors"]:
                    print(f"      ⚠️  {error}")
        
        # Overall result
        print_header("Overall Result")
        if successful_users == total_users:
            print_success("All authentication flows completed successfully!")
            return 0
        else:
            print_warning(f"{failed_users} out of {total_users} flows had issues")
            print_info("Note: Circle connect failures are expected if wallets haven't been created via frontend")
            return 1
    
    except Exception as e:
        print_error(f"Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        await tester.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
