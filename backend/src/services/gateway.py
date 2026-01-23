"""
Circle Gateway Service.
Handles Gateway balance checks (get_balance). x402 create_micropayment/validate_receipt
are deprecated; evaluations are free. Use verifier_client + /verifier for evaluation.
"""

import os
import logging
from decimal import Decimal
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class GatewayService:
    """
    Circle Gateway API client. get_balance is available.
    create_micropayment and validate_receipt are deprecated (x402; evaluations are free).
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
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Deprecated. x402 removed; evaluations are free."""
        raise NotImplementedError("x402 deprecated: evaluations are free. create_micropayment removed.")

    async def validate_receipt(self, receipt: str) -> bool:
        """Deprecated. x402 removed; evaluations are free."""
        raise NotImplementedError("x402 deprecated: evaluations are free. validate_receipt removed.")


# Singleton instance
_gateway_service: Optional[GatewayService] = None


def get_gateway_service() -> GatewayService:
    """Get or create the Gateway service singleton."""
    global _gateway_service
    if _gateway_service is None:
        _gateway_service = GatewayService()
    return _gateway_service
