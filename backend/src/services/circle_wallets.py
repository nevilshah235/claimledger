"""
Circle Wallets Service.
Handles Circle Wallets API interactions for user authentication and wallet management.

Uses Circle Wallets API for user-controlled wallets.
"""

import os
from typing import Optional, Dict, Any, List
import httpx


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
        response.raise_for_status()
        
        return response.json()["data"]
    
    async def initialize_user(self, user_token: str) -> Dict[str, Any]:
        """
        Initialize user authentication challenge.
        
        This generates a challengeId that the frontend SDK uses to authenticate.
        
        Note: For User-Controlled wallets, this requires userToken from frontend SDK.
        
        Args:
            user_token: Circle user token (from frontend SDK authentication)
            
        Returns:
            Challenge data including challengeId
        """
        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")
        
        # For User-Controlled wallets, /user/initialize requires userToken
        # The userToken comes from the frontend SDK after user authenticates
        response = await self.http_client.post(
            f"{self.api_base_url}/user/initialize",
            json={"userToken": user_token}
        )
        response.raise_for_status()
        
        return response.json()["data"]
    
    async def get_user_wallets(
        self, 
        user_id: str, 
        blockchains: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get wallets for a user.
        
        Args:
            user_id: Circle user ID
            blockchains: Optional list of blockchains to filter (e.g., ["ARC"])
            
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
            blockchains: List of blockchains (default: ["ARC"])
            
        Returns:
            Wallet data including walletId and address
        """
        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")
        
        if blockchains is None:
            blockchains = ["ARC"]  # Default to Arc
        
        response = await self.http_client.post(
            f"{self.api_base_url}/wallets",
            json={
                "userId": user_id,
                "blockchains": blockchains
            }
        )
        response.raise_for_status()
        
        return response.json()["data"]["wallet"]
