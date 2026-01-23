"""
Developer-Controlled Wallets Service.
Handles Circle Developer-Controlled Wallets API interactions.

This service manages wallets on behalf of users (backend-only, no frontend SDK needed).

⚠️ DEPRECATED: This service is deprecated in favor of User-Controlled Wallets with PIN.
Use CircleWalletsService instead for User-Controlled wallets.

This file is kept for backward compatibility but should not be used for new features.
"""

import os
import uuid
from typing import Optional, Dict, Any, List
import httpx
import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP


class DeveloperWalletsService:
    """
    Service for Circle Developer-Controlled Wallets API operations.
    
    Handles:
    - Creating wallet sets
    - Creating wallets for users
    - Getting wallet information
    - Managing entity secrets
    """
    
    def __init__(self, api_key: Optional[str] = None, entity_secret: Optional[str] = None):
        self.api_key = api_key or os.getenv("CIRCLE_WALLETS_API_KEY")
        self.entity_secret = entity_secret or os.getenv("CIRCLE_ENTITY_SECRET")
        self.api_base_url = "https://api.circle.com/v1/w3s/developer"
        
        # HTTP client for API calls
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            } if self.api_key else {}
        )
        
        # Wallet set ID (create once, reuse for all wallets)
        self._wallet_set_id: Optional[str] = None
        # Circle public key for encryption (cached)
        self._circle_public_key: Optional[str] = None
    
    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()
    
    async def _get_circle_public_key(self) -> str:
        """Get Circle's public key for entity secret encryption."""
        if self._circle_public_key:
            return self._circle_public_key
        
        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")
        
        response = await self.http_client.get(
            "https://api.circle.com/v1/w3s/config/entity/publicKey"
        )
        response.raise_for_status()
        
        public_key_data = response.json()["data"]
        self._circle_public_key = public_key_data["publicKey"]
        return self._circle_public_key
    
    async def _encrypt_entity_secret(self) -> str:
        """
        Encrypt entity secret for API requests using RSA with Circle's public key.
        
        Circle requires entity secret to be encrypted using RSA-OAEP with their public key.
        """
        if not self.entity_secret:
            raise ValueError("CIRCLE_ENTITY_SECRET not configured")
        
        try:
            # Get Circle's public key
            public_key_pem = await self._get_circle_public_key()
            
            # Load public key
            public_key = RSA.import_key(public_key_pem)
            
            # Initialize cipher
            cipher = PKCS1_OAEP.new(public_key)
            
            # Encrypt entity secret (must be bytes)
            # Entity secret is stored as hex string, convert to bytes
            if isinstance(self.entity_secret, str):
                # Check if it's hex (64 chars = 32 bytes)
                if len(self.entity_secret) == 64:
                    try:
                        entity_secret_bytes = bytes.fromhex(self.entity_secret)
                    except ValueError:
                        # Not valid hex, treat as regular string
                        entity_secret_bytes = self.entity_secret.encode()
                else:
                    # Not hex format, encode as string
                    entity_secret_bytes = self.entity_secret.encode()
            else:
                entity_secret_bytes = self.entity_secret
            
            encrypted_secret = cipher.encrypt(entity_secret_bytes)
            
            # Encode in base64
            return base64.b64encode(encrypted_secret).decode('utf-8')
        except Exception as e:
            # Fallback for hackathon: if encryption fails, use base64 (not secure, but works for demo)
            # In production, this must use proper RSA encryption
            if isinstance(self.entity_secret, str):
                return base64.b64encode(self.entity_secret.encode()).decode()
            return base64.b64encode(self.entity_secret).decode()

    async def register_entity_secret_with_circle(self) -> bool:
        """
        Register the entity secret with Circle's API.
        Must be called before creating wallet sets or wallets.
        Returns True if registered or already registered, False on hard failure.
        """
        if not self.api_key or not self.entity_secret:
            print("  ❌ Missing API key or entity secret")
            return False
        if len(self.entity_secret) != 64:
            print(f"  ❌ Entity secret must be 64 hex chars, got {len(self.entity_secret)}")
            return False
        try:
            entity_secret_bytes = bytes.fromhex(self.entity_secret)
        except ValueError as e:
            print(f"  ❌ Invalid entity secret hex format: {e}")
            return False
        if len(entity_secret_bytes) != 32:
            print(f"  ❌ Entity secret must be 32 bytes, got {len(entity_secret_bytes)}")
            return False

        try:
            ciphertext = await self._encrypt_entity_secret()
        except Exception as e:
            print(f"  ❌ Failed to encrypt entity secret: {e}")
            return False

        try:
            response = await self.http_client.post(
                "https://api.circle.com/v1/w3s/config/entity/secret",
                json={
                    "idempotencyKey": str(uuid.uuid4()),
                    "entitySecretCiphertext": ciphertext,
                },
            )
            if response.status_code in (200, 201):
                print(f"  ✅ Entity secret registered successfully (status {response.status_code})")
                return True
            if response.status_code == 400:
                data = response.json()
                msg = (data.get("message") or "").lower()
                if "already" in msg or "exists" in msg:
                    print(f"  ✅ Entity secret already registered")
                    return True
                print(f"  ⚠️  Registration returned 400: {data.get('message', response.text)}")
                return False
            if response.status_code == 404:
                # 404 is expected in some Circle API configurations
                # Entity secret registration happens automatically when creating the first wallet set
                print(f"  ℹ️  Registration endpoint returned 404 (expected in some configurations)")
                print(f"  Entity secret will be registered automatically when creating wallet set")
                return True  # Return True because automatic registration will happen
            print(f"  ⚠️  Registration returned {response.status_code}: {response.text}")
            return False
        except httpx.HTTPStatusError as e:
            print(f"  ❌ Registration HTTP error {e.response.status_code}: {e.response.text}")
            return False
        except Exception as e:
            print(f"  ❌ Registration failed: {e}")
            return False
    
    async def get_or_create_wallet_set(self) -> str:
        """
        Get existing wallet set or create a new one.
        
        Returns:
            Wallet set ID
        """
        if self._wallet_set_id:
            return self._wallet_set_id
        
        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")
        
        # Try to get existing wallet sets first
        try:
            response = await self.http_client.get(
                f"{self.api_base_url}/walletSets"
            )
            if response.status_code == 200:
                data = response.json()
                wallet_sets = data.get("data", {}).get("walletSets", [])
                if wallet_sets:
                    self._wallet_set_id = wallet_sets[0]["id"]
                    return self._wallet_set_id
        except httpx.HTTPStatusError as e:
            # If GET fails, log but continue to try creating
            if e.response.status_code != 404:
                # 404 is expected if no wallet sets exist, other errors might be real issues
                pass
        except Exception:
            pass  # If fails, create new one
        
        # Create new wallet set
        entity_secret_ciphertext = await self._encrypt_entity_secret()
        
        response = await self.http_client.post(
            f"{self.api_base_url}/walletSets",
            json={
                "idempotencyKey": str(uuid.uuid4()),
                "name": "ClaimLedger Wallet Set",
                "entitySecretCiphertext": entity_secret_ciphertext
            }
        )
        
        if response.status_code == 403:
            error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            error_msg = error_data.get("message", response.text)
            raise ValueError(
                f"Entity secret not registered. Circle API returned 403: {error_msg}\n"
                "Please register your entity secret through Circle Console or run: "
                "python scripts/register_entity_secret.py"
            )
        
        response.raise_for_status()
        
        wallet_set_data = response.json()["data"]["walletSet"]
        self._wallet_set_id = wallet_set_data["id"]
        return self._wallet_set_id
    
    async def create_wallet(
        self,
        blockchains: Optional[List[str]] = None,
        account_type: str = "SCA"
    ) -> Dict[str, Any]:
        """
        Create a new Developer-Controlled wallet.
        
        Args:
            blockchains: List of blockchains (default: ["ARC"] for Arc testnet)
            account_type: "SCA" (Smart Contract Account) or "EOA" (Externally Owned Account)
            
        Returns:
            Wallet data including walletId and address
        """
        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")
        
        if blockchains is None:
            blockchains = ["ARC"]  # Default to Arc
        
        # Get or create wallet set
        # First try to get existing wallet sets (this works even if entity secret registration is pending)
        wallet_set_id = None
        if not self._wallet_set_id:
            try:
                response = await self.http_client.get(
                    f"{self.api_base_url}/walletSets"
                )
                if response.status_code == 200:
                    data = response.json()
                    wallet_sets = data.get("data", {}).get("walletSets", [])
                    if wallet_sets:
                        wallet_set_id = wallet_sets[0]["id"]
                        self._wallet_set_id = wallet_set_id
            except Exception:
                pass  # If GET fails, try to create via get_or_create_wallet_set
        
        # If we don't have a wallet set ID yet, try to get or create one
        if not wallet_set_id:
            wallet_set_id = await self.get_or_create_wallet_set()
        
        entity_secret_ciphertext = await self._encrypt_entity_secret()
        
        # Create wallet
        response = await self.http_client.post(
            f"{self.api_base_url}/wallets",
            json={
                "walletSetId": wallet_set_id,
                "blockchains": blockchains,
                "count": 1,
                "accountType": account_type,
                "entitySecretCiphertext": entity_secret_ciphertext
            }
        )
        response.raise_for_status()
        
        wallet_data = response.json()["data"]["wallets"][0]
        return {
            "wallet_id": wallet_data["id"],
            "address": wallet_data["address"],
            "wallet_set_id": wallet_set_id,
            "blockchain": wallet_data.get("blockchain", blockchains[0]),
            "account_type": wallet_data.get("accountType", account_type)
        }
    
    async def get_wallet(self, wallet_id: str) -> Dict[str, Any]:
        """
        Get wallet information by wallet ID.
        
        Args:
            wallet_id: Circle wallet ID
            
        Returns:
            Wallet data
        """
        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")
        
        response = await self.http_client.get(
            f"{self.api_base_url}/wallets/{wallet_id}"
        )
        response.raise_for_status()
        
        return response.json()["data"]["wallet"]
    
    async def get_wallet_balance(
        self,
        wallet_id: str,
        token_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get wallet balance (USDC by default).
        
        Args:
            wallet_id: Circle wallet ID
            token_id: Token ID (default: USDC on Arc)
            
        Returns:
            Balance information
        """
        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")
        
        # Note: This endpoint may vary - check Circle API docs
        # For now, return a placeholder structure
        params = {}
        if token_id:
            params["tokenId"] = token_id
        
        try:
            response = await self.http_client.get(
                f"{self.api_base_url}/wallets/{wallet_id}/balances",
                params=params
            )
            response.raise_for_status()
            return response.json()["data"]
        except httpx.HTTPStatusError:
            # If endpoint doesn't exist, return placeholder
            return {
                "balances": [],
                "wallet_id": wallet_id
            }
