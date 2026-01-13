"""
Circle Gateway Service.
Handles micropayments via Circle Gateway API.

Uses Circle Gateway for x402 micropayments.
Uses USDC on Arc for settlement.
"""

import os
import uuid
from decimal import Decimal
from typing import Optional, Dict, Any
import httpx


class GatewayService:
    """
    Circle Gateway API client for micropayments.
    
    Handles:
    - Creating micropayments for x402 flows
    - Validating payment receipts
    - Checking balances
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        agent_wallet_address: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("CIRCLE_GATEWAY_API_KEY")
        self.agent_wallet_address = agent_wallet_address or os.getenv("AGENT_WALLET_ADDRESS")
        self.api_base_url = "https://api.circle.com/v1/gateway"
        
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
    
    async def create_micropayment(
        self,
        amount: Decimal,
        payment_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create a micropayment via Circle Gateway.
        
        Args:
            amount: Payment amount in USDC
            payment_id: Unique payment identifier
            metadata: Additional metadata for the payment
            
        Returns:
            Receipt token if successful, None otherwise
        """
        # TODO: Implement actual Circle Gateway API call
        # For now, return mock receipt for demo
        
        if not self.api_key:
            # Demo mode - return mock receipt
            return f"mock_receipt_{payment_id}_{uuid.uuid4().hex[:8]}"
        
        # Production mode - call Gateway API
        try:
            response = await self.http_client.post(
                f"{self.api_base_url}/micropayments",
                json={
                    "amount": str(amount),
                    "currency": "USDC",
                    "recipient": self.agent_wallet_address,
                    "paymentId": payment_id,
                    "metadata": metadata or {}
                }
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("receiptToken")
            
        except httpx.HTTPError as e:
            print(f"Gateway payment error: {e}")
            return None
    
    async def validate_receipt(self, receipt: str) -> bool:
        """
        Validate a payment receipt with Circle Gateway.
        
        Args:
            receipt: Receipt token to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not self.api_key:
            # Demo mode - accept all receipts
            return receipt is not None and len(receipt) > 0
        
        # Production mode - validate with Gateway API
        try:
            response = await self.http_client.post(
                f"{self.api_base_url}/receipts/validate",
                json={"receipt": receipt}
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("valid", False)
            
        except httpx.HTTPError as e:
            print(f"Receipt validation error: {e}")
            return False
    
    async def get_balance(self, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Get USDC balance from Circle Gateway.
        
        Args:
            wallet_address: Wallet address to check (default: agent wallet)
            
        Returns:
            Balance information
        """
        address = wallet_address or self.agent_wallet_address
        
        if not self.api_key:
            # Demo mode - return mock balance
            return {
                "address": address,
                "balance": "1000.00",
                "currency": "USDC",
                "chain": "arc-testnet"
            }
        
        # Production mode - query Gateway API
        try:
            response = await self.http_client.get(
                f"{self.api_base_url}/balances/{address}"
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            print(f"Balance query error: {e}")
            return {
                "address": address,
                "balance": "0.00",
                "currency": "USDC",
                "error": str(e)
            }


# Singleton instance
_gateway_service: Optional[GatewayService] = None


def get_gateway_service() -> GatewayService:
    """Get or create the Gateway service singleton."""
    global _gateway_service
    if _gateway_service is None:
        _gateway_service = GatewayService()
    return _gateway_service
