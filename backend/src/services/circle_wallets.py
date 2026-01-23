"""
Circle Wallets Service.
Handles Circle Wallets API interactions for user authentication and wallet management.

Uses Circle Wallets API for user-controlled wallets.
"""

import os
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
import httpx
from dotenv import load_dotenv

# Load .env from backend directory (where this file is located)
# Go up from src/services/circle_wallets.py to backend/
backend_dir = Path(__file__).parent.parent.parent
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)


class CircleWalletsService:
    """
    Service for Circle Wallets API operations.
    
    Handles:
    - Creating/retrieving users
    - Initializing authentication challenges
    - Getting user wallets
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CIRCLE_WALLETS_API_KEY")
        self.app_id = os.getenv("CIRCLE_APP_ID")
        self.api_base_url = "https://api.circle.com/v1/w3s"
        
        # HTTP client for API calls
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            } if self.api_key else {}
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()
    
    def validate_app_id(self) -> bool:
        """
        Validate that App ID is set and not empty.
        
        Returns:
            True if App ID is valid, False otherwise
        """
        return bool(self.app_id and self.app_id.strip())
    
    async def create_user(self, user_id: str) -> Dict[str, Any]:
        """
        Create or retrieve a Circle user.
        
        Args:
            user_id: Unique user identifier (e.g., email, UUID)
            
        Returns:
            User data including userToken
        """
        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")
        
        response = await self.http_client.post(
            f"{self.api_base_url}/users",
            json={"userId": user_id}
        )
        
        # 409 Conflict means user already exists - that's fine, return success
        if response.status_code == 409:
            # User already exists, try to get user info
            # Note: Circle API doesn't have a direct "get user" endpoint,
            # but we can proceed as if creation succeeded
            return {"id": user_id, "userId": user_id}
        
        response.raise_for_status()
        
        return response.json()["data"]
    
    async def initialize_user(
        self, 
        user_token: str,
        account_type: Optional[str] = None,
        blockchains: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Initialize user authentication challenge.
        
        This generates a challengeId that the frontend SDK uses to authenticate.
        
        Circle endpoint: POST /v1/w3s/user/initialize
        Requires X-User-Token header.
        
        Args:
            user_token: Circle user token (from create_user_token)
            account_type: Optional account type (e.g., "SCA")
            blockchains: Optional list of blockchains (e.g., ["ARC-TESTNET"])
            
        Returns:
            Challenge data including challengeId
        """
        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")
        
        # Build request body
        request_body = {
            "idempotencyKey": str(uuid.uuid4())
        }
        if account_type:
            request_body["accountType"] = account_type
        if blockchains:
            request_body["blockchains"] = blockchains
        
        # For User-Controlled wallets, /user/initialize requires userToken in header
        response = await self.http_client.post(
            f"{self.api_base_url}/user/initialize",
            headers={
                "X-User-Token": user_token
            },
            json=request_body
        )
        
        # 409 means user is already initialized - that's OK, they should have a wallet
        if response.status_code == 409:
            error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            error_code = error_data.get("code")
            if error_code == 155106:  # User already initialized
                # User is already initialized - return empty challenge (no challenge needed)
                return {"challengeId": None, "alreadyInitialized": True}
        
        response.raise_for_status()
        
        return response.json()["data"]

    async def create_user_token(self, user_id: str) -> Dict[str, Any]:
        """
        Create a user session token for the Web SDK (PIN flow).

        Circle endpoint: POST /v1/w3s/users/token

        Returns:
            { "userToken": "...", "encryptionKey": "..." }
        """
        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")

        response = await self.http_client.post(
            f"{self.api_base_url}/users/token",
            json={"userId": user_id},
        )
        response.raise_for_status()
        return response.json()["data"]
    
    async def get_user_wallets(
        self, 
        user_id: str, 
        blockchains: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get wallets for a user using user ID.
        
        Args:
            user_id: Circle user ID
            blockchains: Optional list of blockchains to filter (e.g., ["ARC-TESTNET"])
            
        Returns:
            List of wallet objects
        """
        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")
        
        params = {}
        if blockchains:
            params["blockchains"] = ",".join(blockchains)
        
        response = await self.http_client.get(
            f"{self.api_base_url}/users/{user_id}/wallets",
            params=params
        )
        
        # 404 means user has no wallets yet - return empty list (not an error)
        if response.status_code == 404:
            return []
        
        response.raise_for_status()
        
        return response.json()["data"].get("wallets", [])
    
    async def list_wallets(self, user_token: str) -> List[Dict[str, Any]]:
        """
        List wallets for a user using user token (User-Controlled wallets).
        
        Circle endpoint: GET /v1/w3s/wallets
        Requires X-User-Token header.
        
        Args:
            user_token: Circle user token from create_user_token()
            
        Returns:
            List of wallet objects
        """
        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")
        
        response = await self.http_client.get(
            f"{self.api_base_url}/wallets",
            headers={
                "X-User-Token": user_token
            }
        )
        response.raise_for_status()
        
        return response.json()["data"].get("wallets", [])
    
    async def create_wallet(
        self,
        user_id: str,
        blockchains: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new wallet for a user.
        
        Args:
            user_id: Circle user ID
            blockchains: List of blockchains (default: ["ARC-TESTNET"])
            
        Returns:
            Wallet data including walletId and address
        """
        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")
        
        if blockchains is None:
            blockchains = ["ARC-TESTNET"]  # Default to Arc Testnet
        
        response = await self.http_client.post(
            f"{self.api_base_url}/wallets",
            json={
                "userId": user_id,
                "blockchains": blockchains
            }
        )
        response.raise_for_status()
        
        return response.json()["data"]["wallet"]
