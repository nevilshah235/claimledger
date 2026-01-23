#!/usr/bin/env python3
"""
Validate Circle Credentials

Quick script to check if CIRCLE_WALLETS_API_KEY and CIRCLE_APP_ID are valid.

Usage:
    python backend/scripts/validate_circle_credentials.py
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

from src.services.circle_wallets import CircleWalletsService


class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    OKBLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_success(text: str):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_error(text: str):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def print_warning(text: str):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


def print_info(text: str):
    print(f"{Colors.OKBLUE}ℹ️  {text}{Colors.ENDC}")


async def validate_credentials():
    """Validate Circle API credentials."""
    print(f"\n{Colors.BOLD}Validating Circle Credentials{Colors.ENDC}\n")
    
    api_key = os.getenv("CIRCLE_WALLETS_API_KEY")
    app_id = os.getenv("CIRCLE_APP_ID")
    
    # Check if set
    if not api_key:
        print_error("CIRCLE_WALLETS_API_KEY not set")
        print_info("Set it in backend/.env or as environment variable")
        return False
    
    if not app_id:
        print_error("CIRCLE_APP_ID not set")
        print_info("Set it in backend/.env or as environment variable")
        return False
    
    print_success("CIRCLE_WALLETS_API_KEY is set")
    print_success("CIRCLE_APP_ID is set")
    print_info(f"App ID: {app_id[:20]}...")
    
    # Test API key
    print("\nTesting API key...")
    circle_service = CircleWalletsService()
    
    try:
        # Try to get Circle's public key (simple endpoint that validates API key)
        response = await circle_service.http_client.get(
            "https://api.circle.com/v1/w3s/config/entity/publicKey"
        )
        
        if response.status_code == 200:
            print_success("API key is valid")
        elif response.status_code == 401:
            print_error("API key is invalid or unauthorized")
            print_info("Check your CIRCLE_WALLETS_API_KEY in Circle Developer Console")
            return False
        else:
            print_warning(f"Unexpected response: {response.status_code}")
            print_info(f"Response: {response.text[:200]}")
    except Exception as e:
        print_error(f"Failed to validate API key: {e}")
        return False
    
    # Test App ID by trying to create a test user
    print("\nTesting App ID...")
    try:
        test_user_id = "test-validation-user"
        response = await circle_service.http_client.post(
            f"{circle_service.api_base_url}/users",
            json={"userId": test_user_id}
        )
        
        if response.status_code in (200, 201):
            print_success("App ID appears to be valid (user creation succeeded)")
            # Clean up test user
            try:
                await circle_service.http_client.delete(
                    f"{circle_service.api_base_url}/users/{test_user_id}"
                )
            except:
                pass  # Ignore cleanup errors
        elif response.status_code == 400:
            error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            error_msg = error_data.get("message", response.text)
            
            if "app" in error_msg.lower() and "id" in error_msg.lower():
                print_error("App ID is not recognized")
                print_info("The CIRCLE_APP_ID doesn't match your Circle account")
                print_info("\nHow to fix:")
                print_info("1. Go to Circle Developer Console: https://console.circle.com")
                print_info("2. Navigate to your Wallets app")
                print_info("3. Copy the App ID from the app settings")
                print_info("4. Update CIRCLE_APP_ID in backend/.env")
                return False
            else:
                print_warning(f"Unexpected error: {error_msg}")
        elif response.status_code == 401:
            print_error("API key is invalid")
            return False
        else:
            print_warning(f"Unexpected response: {response.status_code}")
            print_info(f"Response: {response.text[:200]}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            error_data = e.response.json() if e.response.headers.get("content-type", "").startswith("application/json") else {}
            error_msg = error_data.get("message", str(e))
            
            if "app" in error_msg.lower() and "id" in error_msg.lower() or "not recognized" in error_msg.lower():
                print_error("App ID is not recognized by Circle")
                print_info("\nHow to fix:")
                print_info("1. Go to Circle Developer Console: https://console.circle.com")
                print_info("2. Navigate to your Wallets app")
                print_info("3. Copy the App ID from the app settings")
                print_info("4. Update CIRCLE_APP_ID in backend/.env")
                print_info("\nNote: App ID must match the app associated with your API key")
                return False
            else:
                print_warning(f"Error: {error_msg}")
        else:
            print_error(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
    except Exception as e:
        print_error(f"Failed to validate App ID: {e}")
        return False
    
    await circle_service.close()
    
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}✅ All credentials are valid!{Colors.ENDC}")
    return True


if __name__ == "__main__":
    success = asyncio.run(validate_credentials())
    sys.exit(0 if success else 1)
