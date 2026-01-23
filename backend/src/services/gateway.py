"""
Circle Gateway Service.
Handles micropayments via Circle Gateway API.

Uses Circle Gateway for x402 micropayments.
Uses USDC on Arc for settlement.
"""

import os
import uuid
import logging
from decimal import Decimal
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)


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
        # Legacy support: agent_wallet_address can still be set for backward compatibility
        # But new code should pass wallet_address to create_micropayment directly
        self.agent_wallet_address = agent_wallet_address or os.getenv("AGENT_WALLET_ADDRESS")
        # Circle Gateway API base URL
        # Gateway balances API uses gateway-api.circle.com/v1
        # For testnet: gateway-api-testnet.circle.com/v1
        # Check API key to determine environment
        if self.api_key:
            if self.api_key.startswith("TEST_API_KEY:") or self.api_key.startswith("SAND_KEY_"):
                self.gateway_api_url = "https://gateway-api-testnet.circle.com/v1"
            else:
                self.gateway_api_url = "https://gateway-api.circle.com/v1"
        else:
            self.gateway_api_url = "https://gateway-api-testnet.circle.com/v1"  # Default to testnet
        
        # Legacy API base URL (for other endpoints if needed)
        self.api_base_url = "https://api.circle.com/v1/gateway"
        
        # Arc blockchain domain ID (from Circle Gateway docs)
        self.arc_domain = 26
        
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
    
    async def get_balance(
        self,
        depositor_address: Optional[str] = None,
        domain: Optional[int] = None
    ) -> Optional[Decimal]:
        """
        Get Gateway USDC balance for a depositor address.
        
        Args:
            depositor_address: Wallet address to check (default: agent_wallet_address)
            domain: Blockchain domain ID (default: Arc domain 26)
            
        Returns:
            Balance in USDC as Decimal, or None if check failed
        """
        if not self.api_key:
            logger.debug("No API key, skipping balance check")
            return None
        
        address = depositor_address or self.agent_wallet_address
        if not address:
            logger.debug("No depositor address provided, skipping balance check")
            return None
        
        domain_id = domain or self.arc_domain
        
        try:
            response = await self.http_client.post(
                f"{self.gateway_api_url}/balances",
                json={
                    "token": "USDC",
                    "sources": [
                        {
                            "depositor": address,
                            "domain": domain_id
                        }
                    ]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.debug(f"Gateway API response: {data}")
                
                # Gateway API might return balances in different formats
                # Try multiple possible response structures
                balances = data.get("balances", [])
                if not balances:
                    # Try alternative structure
                    balances = data.get("data", {}).get("balances", [])
                
                if balances:
                    # Balance is returned as string decimal
                    balance_str = balances[0].get("balance", "0")
                    balance = Decimal(balance_str)
                    logger.info(
                        f"Gateway balance for {address[:10]}... on domain {domain_id}: "
                        f"{balance} USDC (raw: {balance_str})"
                    )
                    return balance
                else:
                    logger.warning(
                        f"No balance found for {address[:10]}... on domain {domain_id}. "
                        f"Response structure: {list(data.keys())}"
                    )
                    return Decimal("0")
            else:
                logger.warning(
                    f"Gateway balance API returned {response.status_code}: {response.text[:200]}"
                )
                return None
                
        except httpx.HTTPError as e:
            logger.warning(f"Failed to check Gateway balance: {e}")
            return None
        except Exception as e:
            logger.error(f"Error checking Gateway balance: {e}")
            return None
    
    async def create_micropayment(
        self,
        amount: Decimal,
        payment_id: str,
        wallet_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create a micropayment receipt via Circle Gateway.
        
        For x402 micropayments, we issue a receipt token that proves payment.
        The actual USDC movement can be tracked via Gateway balances.
        
        Args:
            amount: Payment amount in USDC
            payment_id: Unique payment identifier (used as idempotency key)
            metadata: Additional metadata for the payment
            
        Returns:
            Receipt token if successful, None otherwise
            
        Note:
            Circle Gateway doesn't have a direct micropayment endpoint.
            For x402, we:
            1. Verify agent has sufficient balance via Gateway balances API
            2. Issue a receipt token (payment_id signed/encoded)
            3. Track payment in our system
            4. Actual USDC settlement can happen via Gateway transfers if needed
        """
        if not self.api_key:
            # Demo mode - return mock receipt
            logger.info(f"Mock mode: Creating mock receipt for payment {payment_id}")
            return f"mock_receipt_{payment_id}_{uuid.uuid4().hex[:8]}"
        
        # Convert amount to USDC format (6 decimals)
        # USDC uses 6 decimal places, so 0.10 USDC = 100000 (raw units)
        amount_raw = int(amount * Decimal("1000000"))
        
        # Use provided wallet_address or fall back to agent_wallet_address for backward compatibility
        wallet_to_check = wallet_address or self.agent_wallet_address
        
        # Verify Gateway balance if wallet is configured
        if wallet_to_check:
            logger.info(f"Verifying Gateway balance for payment of {amount} USDC (wallet: {wallet_to_check[:10]}...)")
            current_balance = await self.get_balance(wallet_to_check)
            
            if current_balance is not None:
                if current_balance < amount:
                    logger.error(
                        f"Insufficient Gateway balance: {current_balance} USDC < "
                        f"{amount} USDC required for payment {payment_id} (wallet: {wallet_to_check[:10]}...)"
                    )
                    return None
                else:
                    logger.info(
                        f"Gateway balance verified: {current_balance} USDC available, "
                        f"{amount} USDC required - sufficient funds (wallet: {wallet_to_check[:10]}...)"
                    )
            else:
                # Balance check failed (API error, network issue, etc.)
                # For x402, we can still issue receipt but log warning
                # In production, you might want to fail here instead
                logger.warning(
                    f"Could not verify Gateway balance (API unavailable or wallet not found), "
                    f"but proceeding with receipt issuance. Payment ID: {payment_id}. "
                    f"Wallet: {wallet_to_check[:10]}... Consider checking balance manually."
                )
        else:
            logger.info(
                "Wallet address not provided and agent wallet not configured, issuing receipt without balance verification"
            )
        
        # Issue receipt token
        logger.info(f"Issuing x402 payment receipt for {amount} USDC (payment_id: {payment_id})")
        
        # Issue receipt token
        # For x402, the receipt is a proof of payment
        # Format: base64(payment_id:hash) where hash is derived from payment_id + api_key
        import hashlib
        import base64
        
        # Create receipt hash from payment_id and API key (first 20 chars for consistency)
        receipt_hash = hashlib.sha256(
            f"{payment_id}:{self.api_key[:20]}".encode()
        ).hexdigest()[:16]
        
        # Encode as base64: payment_id:hash
        receipt_token = base64.urlsafe_b64encode(
            f"{payment_id}:{receipt_hash}".encode()
        ).decode('utf-8').rstrip('=')
        
        logger.info(f"Payment receipt issued: {payment_id} -> {receipt_token[:50]}...")
        return receipt_token
    
    async def validate_receipt(self, receipt: str) -> bool:
        """
        Validate a payment receipt.
        
        For x402 micropayments, receipts are tokens we issue ourselves.
        We validate by:
        1. Decoding the receipt token
        2. Verifying the format and signature
        3. Checking if payment_id exists in our system (optional)
        
        Args:
            receipt: Receipt token to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not receipt:
            return False
            
        if not self.api_key:
            # Demo mode - accept all non-empty receipts
            logger.debug(f"Mock mode: Accepting receipt {receipt[:20]}...")
            return len(receipt) > 0
        
        # Production mode - validate receipt format
        try:
            import base64
            import hashlib
            
            # Decode receipt token
            # Format: base64(payment_id:hash)
            try:
                # Add padding if needed
                receipt_padded = receipt + '=' * (4 - len(receipt) % 4)
                decoded = base64.urlsafe_b64decode(receipt_padded).decode('utf-8')
                
                if ':' not in decoded:
                    logger.warning(f"Invalid receipt format: missing separator")
                    return False
                
                payment_id, receipt_hash = decoded.split(':', 1)
                
                # Verify receipt hash matches expected format
                # Receipt should be: payment_id:hash where hash is derived from payment_id + api_key
                expected_hash = hashlib.sha256(
                    f"{payment_id}:{self.api_key[:20]}".encode()
                ).hexdigest()[:16]
                
                if receipt_hash == expected_hash:
                    logger.info(f"Receipt validated successfully: {payment_id}")
                    return True
                else:
                    logger.warning(f"Receipt hash mismatch for payment_id: {payment_id}")
                    return False
                    
            except (ValueError, UnicodeDecodeError) as e:
                logger.warning(f"Failed to decode receipt: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error validating receipt: {e}")
            return False


# Singleton instance
_gateway_service: Optional[GatewayService] = None


def get_gateway_service() -> GatewayService:
    """Get or create the Gateway service singleton."""
    global _gateway_service
    if _gateway_service is None:
        _gateway_service = GatewayService()
    return _gateway_service
