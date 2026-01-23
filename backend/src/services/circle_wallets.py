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
        import logging
        logging.info(f"Calling Circle initialize_user API with body: {request_body}")
        
        response = await self.http_client.post(
            f"{self.api_base_url}/user/initialize",
            headers={
                "X-User-Token": user_token
            },
            json=request_body
        )
        
        logging.info(f"Circle initialize_user response status: {response.status_code}")
        
        # 409 means user is already initialized - that's OK, they should have a wallet
        if response.status_code == 409:
            error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            error_code = error_data.get("code")
            error_message = error_data.get("message", "")
            logging.warning(f"Circle API returned 409 (Conflict): code={error_code}, message={error_message}")
            logging.warning(f"Full error response: {error_data}")
            
            if error_code == 155106:  # User already initialized
                # User is already initialized - return empty challenge (no challenge needed)
                logging.info("User is already initialized in Circle - no challenge_id available")
                return {"challengeId": None, "alreadyInitialized": True}
        
        response.raise_for_status()
        
        response_data = response.json()
        challenge_id = response_data.get("data", {}).get("challengeId")
        logging.info(f"Circle initialize_user successful - challenge_id: {challenge_id}")
        logging.info(f"Full response data: {response_data}")
        
        return response_data["data"]

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
        Developer-style API: GET /users/{user_id}/wallets (no X-User-Token).
        For user-controlled wallets, prefer list_wallets(user_token) which uses
        GET /wallets with X-User-Token.

        Args:
            user_id: Circle user ID
            blockchains: Optional list of blockchains to filter (e.g., ["ARC-TESTNET"])

        Returns:
            List of wallet objects
        """
        import logging

        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")

        params = {}
        if blockchains:
            params["blockchains"] = ",".join(blockchains)

        url = f"{self.api_base_url}/users/{user_id}/wallets"
        logging.info(f"Querying Circle API: GET {url} with params: {params}")
        
        response = await self.http_client.get(url, params=params)
        
        # 404 means user has no wallets yet - return empty list (not an error)
        if response.status_code == 404:
            logging.info(f"Circle API returned 404 for user {user_id} - no wallets found")
            return []
        
        response.raise_for_status()
        
        response_data = response.json()
        logging.info(f"Circle API full response for user {user_id}: {response_data}")
        
        wallets = response_data.get("data", {}).get("wallets", [])
        logging.info(f"Circle API returned {len(wallets)} wallet(s) for user {user_id}")
        
        if wallets:
            for i, wallet in enumerate(wallets):
                wallet_id = wallet.get("walletId") or wallet.get("id") or wallet.get("wallet_id")
                address = wallet.get("address")
                blockchain = wallet.get("blockchain")
                logging.info(f"  Wallet {i+1}: id={wallet_id}, address={address}, blockchain={blockchain}")
                logging.info(f"  Full wallet data: {wallet}")
        else:
            logging.warning(f"No wallets in response data. Full response structure: {response_data}")
            # Check if there's data but no wallets key
            data = response_data.get("data", {})
            if data and "wallets" not in data:
                logging.warning(f"Response has 'data' key but no 'wallets' key. Data keys: {list(data.keys())}")
        
        return wallets
    
    async def list_wallets(self, user_token: str) -> List[Dict[str, Any]]:
        """
        List wallets for a user using user token (User-Controlled wallets).
        
        Circle endpoint: GET /v1/w3s/wallets
        Requires X-User-Token header.
        
        This is the correct endpoint for User-Controlled wallets (not get_user_wallets).
        
        Args:
            user_token: Circle user token from create_user_token()
            
        Returns:
            List of wallet objects
        """
        import logging
        
        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")
        
        url = f"{self.api_base_url}/wallets"
        logging.info(f"Querying Circle API (User-Controlled wallets): GET {url} with X-User-Token header")
        
        response = await self.http_client.get(
            url,
            headers={
                "X-User-Token": user_token
            }
        )
        
        # 404 means user has no wallets yet - return empty list (not an error)
        if response.status_code == 404:
            logging.info(f"Circle API returned 404 for user token - no wallets found")
            return []
        
        response.raise_for_status()
        
        response_data = response.json()
        logging.info(f"Circle API full response (User-Controlled wallets): {response_data}")
        
        wallets = response_data.get("data", {}).get("wallets", [])
        logging.info(f"Circle API returned {len(wallets)} wallet(s) using user token endpoint")
        
        if wallets:
            for i, wallet in enumerate(wallets):
                wallet_id = wallet.get("walletId") or wallet.get("id") or wallet.get("wallet_id")
                address = wallet.get("address")
                blockchain = wallet.get("blockchain")
                logging.info(f"  Wallet {i+1}: id={wallet_id}, address={address}, blockchain={blockchain}")
                logging.info(f"  Full wallet data: {wallet}")
        else:
            logging.warning(f"No wallets in response data. Full response structure: {response_data}")
        
        return wallets
    
    async def create_wallet(
        self,
        user_id: str,
        blockchains: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new wallet (developer-style: POST /wallets with userId).
        For user-controlled wallets, creation happens via /user/initialize + SDK;
        this is for developer-controlled or legacy flows.

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
    
    async def get_wallet_balance(
        self,
        wallet_id: str,
        chain: Optional[str] = "ARC",
        user_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get wallet balance from Circle API.

        User-controlled wallets: pass user_token (from create_user_token) so
        X-User-Token is sent; otherwise Circle may 403/404. Developer-controlled
        wallets use only the Bearer token.

        Args:
            wallet_id: Circle wallet ID
            chain: Blockchain chain identifier (default: "ARC" for ARC-TESTNET)
            user_token: For user-controlled wallets, from create_user_token().
                        Enables X-User-Token header required by GET /wallets/{id}/balances.

        Returns:
            Balance information with tokenBalances (as "balances" in our response)
        """
        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")

        headers = {"X-User-Token": user_token} if user_token else {}
        try:
            response = await self.http_client.get(
                f"{self.api_base_url}/wallets/{wallet_id}/balances",
                params={"chain": chain},
                headers=headers,
            )
            response.raise_for_status()
            data = response.json().get("data", {})
            token_balances = data.get("tokenBalances", [])
            
            import logging
            logging.info(f"Fetched balance for wallet {wallet_id}: {len(token_balances)} token(s)")
            if token_balances:
                for tb in token_balances:
                    logging.info(f"  Token: {tb.get('token', {}).get('symbol', 'UNKNOWN')}, Amount: {tb.get('amount', '0')}")
            
            return {
                "balances": token_balances,
                "wallet_id": wallet_id
            }
        except httpx.HTTPStatusError as e:
            # If endpoint doesn't exist or returns error, log and return empty balance
            import logging
            logging.warning(f"Could not fetch balance for wallet {wallet_id}: {e.response.status_code} - {e.response.text}")
            return {
                "balances": [],
                "wallet_id": wallet_id
            }
        except Exception as e:
            import logging
            logging.error(f"Error fetching balance for wallet {wallet_id}: {e}")
            return {
                "balances": [],
                "wallet_id": wallet_id
            }

    async def create_user_contract_execution_challenge(
        self,
        user_token: str,
        wallet_id: str,
        contract_address: str,
        abi_function_signature: str,
        abi_parameters: List[Any],
        idempotency_key: Optional[str] = None,
        fee_level: str = "MEDIUM",
        blockchain: str = "ARC-TESTNET",
    ) -> Dict[str, Any]:
        """
        Create a challenge for executing a smart contract from a user-controlled wallet.

        Circle endpoint: POST /v1/w3s/user/transactions/contractExecution

        Args:
            user_token: Circle user token (from create_user_token).
            wallet_id: Circle wallet ID (source of the transaction).
            contract_address: Contract to call.
            abi_function_signature: e.g. "approve(address,uint256)" or "depositEscrow(uint256,uint256)".
            abi_parameters: List of parameters (strings, ints, addresses).
            idempotency_key: UUID v4; generated if not provided.
            fee_level: LOW, MEDIUM, or HIGH.
            blockchain: e.g. "ARC-TESTNET".

        Returns:
            {"challengeId": str} from Circle. The frontend uses sdk.execute(challengeId, callback).
        """
        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")

        key = idempotency_key or str(uuid.uuid4())
        body: Dict[str, Any] = {
            "idempotencyKey": key,
            "walletId": wallet_id,
            "contractAddress": contract_address,
            "abiFunctionSignature": abi_function_signature,
            "abiParameters": abi_parameters,
            "feeLevel": fee_level,
            "blockchain": blockchain,
        }

        import logging
        logging.info(
            "Calling Circle create_user_contract_execution_challenge: contract=%s, fn=%s",
            contract_address[:10] + "...",
            abi_function_signature,
        )

        response = await self.http_client.post(
            f"{self.api_base_url}/user/transactions/contractExecution",
            headers={"X-User-Token": user_token},
            json=body,
        )
        response.raise_for_status()
        data = response.json().get("data", {})
        return data

    async def list_user_transactions(
        self,
        user_token: str,
        wallet_ids: Optional[List[str]] = None,
        operation: Optional[str] = None,
        page_size: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        List user transactions (for fallback when SDK execute does not return transactionId).

        Circle endpoint: GET /v1/w3s/transactions
        Requires X-User-Token. Use walletIds, operation=CONTRACT_EXECUTION to find settlement txs.

        Returns:
            List of transaction objects (each has id, state, txHash, createDate, ...).
        """
        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")
        params: Dict[str, Any] = {"pageSize": page_size}
        if wallet_ids:
            params["walletIds"] = ",".join(wallet_ids)
        if operation:
            params["operation"] = operation
        response = await self.http_client.get(
            f"{self.api_base_url}/transactions",
            headers={"X-User-Token": user_token},
            params=params,
        )
        response.raise_for_status()
        data = response.json().get("data", {})
        return data.get("transactions") or []

    async def get_user_transaction(
        self, transaction_id: str, user_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a user transaction by ID (for /complete to resolve txHash).

        Circle endpoint: GET /v1/w3s/transactions/{id}
        (Not /user/transactions/{id} - List uses /transactions, Get uses the same base.)
        Requires X-User-Token for user-controlled wallets.

        Response: {"data": {"transaction": {...}}} -> we return the inner transaction.

        Args:
            transaction_id: Circle transaction ID (from SDK execute result or list;
                do not pass challengeId).
            user_token: Required for user-controlled wallets; enables X-User-Token.

        Returns:
            {"id": str, "state": str, "txHash": str | None, ...}
        """
        if not self.api_key:
            raise ValueError("CIRCLE_WALLETS_API_KEY not configured")

        kwargs: Dict[str, Any] = {}
        if user_token:
            kwargs["headers"] = {"X-User-Token": user_token}

        response = await self.http_client.get(
            f"{self.api_base_url}/transactions/{transaction_id}",
            **kwargs,
        )
        response.raise_for_status()
        data = response.json().get("data", {})
        return data.get("transaction") or data
