"""
x402 HTTP Client.
Handles HTTP 402 Payment Required responses by paying via Circle Gateway.

Uses Circle Gateway for x402 micropayments.
"""

import os
from decimal import Decimal
from typing import Optional, Dict, Any
import httpx

from .gateway import GatewayService


class X402Client:
    """
    HTTP client that automatically handles x402 (HTTP 402) payment flows.
    
    When a request returns HTTP 402 Payment Required:
    1. Extract payment details from response
    2. Pay via Circle Gateway
    3. Retry request with payment receipt
    """
    
    def __init__(
        self,
        gateway_service: Optional[GatewayService] = None,
        base_url: str = "http://localhost:8000"
    ):
        self.gateway = gateway_service or GatewayService()
        self.base_url = base_url
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()
    
    async def call_with_payment(
        self,
        url: str,
        data: Dict[str, Any],
        claim_id: str,
        wallet_address: Optional[str] = None,
        method: str = "POST"
    ) -> Dict[str, Any]:
        """
        Make an HTTP request, handling x402 payment if required.
        
        Args:
            url: Endpoint URL (relative to base_url or absolute)
            data: Request payload
            claim_id: Claim ID for tracking payments
            method: HTTP method (default: POST)
            
        Returns:
            Response data from the endpoint
            
        Raises:
            X402PaymentError: If payment fails
            httpx.HTTPError: For other HTTP errors
        """
        # Build full URL if relative
        full_url = url if url.startswith("http") else f"{self.base_url}{url}"
        
        # Make initial request
        response = await self.http_client.request(
            method=method,
            url=full_url,
            json=data
        )
        
        # Check for 402 Payment Required
        if response.status_code == 402:
            # Extract payment details
            payment_details = response.json()
            amount = Decimal(response.headers.get("X-Payment-Amount", payment_details.get("amount", "0")))
            payment_id = payment_details.get("gateway_payment_id")
            description = response.headers.get("X-Payment-Description", "x402 payment")
            
            # Pay via Gateway using provided wallet address
            receipt = await self.gateway.create_micropayment(
                amount=amount,
                payment_id=payment_id,
                wallet_address=wallet_address,
                metadata={
                    "claim_id": claim_id,
                    "description": description
                }
            )
            
            if not receipt:
                raise X402PaymentError(f"Failed to create payment for {description}")
            
            # Retry with receipt
            response = await self.http_client.request(
                method=method,
                url=full_url,
                json=data,
                headers={"X-Payment-Receipt": receipt}
            )
        
        # Check for other errors
        response.raise_for_status()
        
        return response.json()
    
    async def verify_document(self, claim_id: str, document_path: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Call document verification endpoint with x402 handling.
        
        Price: $0.05 USDC
        """
        return await self.call_with_payment(
            url="/verifier/document",
            data={
                "claim_id": claim_id,
                "document_path": document_path
            },
            claim_id=claim_id,
            wallet_address=wallet_address
        )
    
    async def verify_image(self, claim_id: str, image_path: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Call image analysis endpoint with x402 handling.
        
        Price: $0.10 USDC
        """
        return await self.call_with_payment(
            url="/verifier/image",
            data={
                "claim_id": claim_id,
                "image_path": image_path
            },
            claim_id=claim_id,
            wallet_address=wallet_address
        )
    
    async def verify_fraud(self, claim_id: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Call fraud check endpoint with x402 handling.
        
        Price: $0.05 USDC
        """
        return await self.call_with_payment(
            url="/verifier/fraud",
            data={
                "claim_id": claim_id
            },
            claim_id=claim_id,
            wallet_address=wallet_address
        )


class X402PaymentError(Exception):
    """Error during x402 payment process."""
    pass


# Singleton instance for convenience
_x402_client: Optional[X402Client] = None


def get_x402_client() -> X402Client:
    """Get or create the x402 client singleton."""
    global _x402_client
    if _x402_client is None:
        _x402_client = X402Client()
    return _x402_client
