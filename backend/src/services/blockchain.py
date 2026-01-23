"""
Blockchain Service.
Handles interactions with Arc blockchain and ClaimEscrow contract.

Uses USDC on Arc for settlement.
When AUTO_SETTLE_PRIVATE_KEY is set, approve_claim runs the real 3-step
(USDC.approve, depositEscrow, approveClaim) via web3. Otherwise mock.
"""

import logging
import os
from decimal import Decimal
from typing import Optional, Dict, Any

from web3 import Web3
from web3.providers import HTTPProvider

from . import arc_rpc
from .arc_rpc import USDC_ABI

logger = logging.getLogger(__name__)

# Contract configuration
CLAIM_ESCROW_ADDRESS = os.getenv("CLAIM_ESCROW_ADDRESS", "0x80794995149E5d26F22c36eD56B817CBd8E5d4Fa")
USDC_ADDRESS = os.getenv("USDC_ADDRESS", "0x3600000000000000000000000000000000000000")
ARC_RPC_URL = os.getenv("ARC_RPC_URL", "https://rpc.testnet.arc.network")
ARC_CHAIN_ID = int(os.getenv("ARC_CHAIN_ID", "11124"))

# ClaimEscrow ABI (minimal for our functions)
CLAIM_ESCROW_ABI = [
    {
        "name": "depositEscrow",
        "type": "function",
        "inputs": [
            {"name": "claimId", "type": "uint256"},
            {"name": "amount", "type": "uint256"}
        ],
        "outputs": []
    },
    {
        "name": "approveClaim",
        "type": "function",
        "inputs": [
            {"name": "claimId", "type": "uint256"},
            {"name": "amount", "type": "uint256"},
            {"name": "recipient", "type": "address"}
        ],
        "outputs": []
    },
    {
        "name": "getEscrowBalance",
        "type": "function",
        "inputs": [{"name": "claimId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view"
    },
    {
        "name": "isSettled",
        "type": "function",
        "inputs": [{"name": "claimId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view"
    }
]


class BlockchainService:
    """
    Service for interacting with Arc blockchain.
    
    Handles:
    - Depositing USDC to escrow
    - Approving and settling claims
    - Querying contract state
    """
    
    def __init__(
        self,
        rpc_url: Optional[str] = None,
        private_key: Optional[str] = None,
        escrow_address: Optional[str] = None
    ):
        self.rpc_url = rpc_url or ARC_RPC_URL
        self.private_key = private_key or os.getenv("INSURER_WALLET_PRIVATE_KEY")
        self.escrow_address = escrow_address or CLAIM_ESCROW_ADDRESS
        self.auto_settle_private_key = os.getenv("AUTO_SETTLE_PRIVATE_KEY")
    
    def claim_id_to_uint256(self, claim_id: str) -> int:
        """
        Convert claim UUID to uint256 for contract.
        Uses first 8 bytes of UUID as claim ID.
        """
        # Remove hyphens and take first 16 hex chars (8 bytes)
        hex_str = claim_id.replace("-", "")[:16]
        return int(hex_str, 16)
    
    def usdc_to_contract_amount(self, amount: Decimal) -> int:
        """
        Convert USDC amount to contract format (6 decimals).
        
        $1.00 = 1000000
        $3,500.00 = 3500000000
        """
        return int(amount * Decimal("1000000"))
    
    async def deposit_escrow(
        self,
        claim_id: str,
        amount: Decimal,
        from_address: str
    ) -> Optional[str]:
        """
        Deposit USDC into escrow for a claim.
        
        Requires prior USDC approval from the depositor.
        
        Args:
            claim_id: Claim identifier
            amount: Amount in USDC
            from_address: Address depositing the funds
            
        Returns:
            Transaction hash if successful
        """
        # TODO: Implement actual blockchain call
        # contract_claim_id = self.claim_id_to_uint256(claim_id)
        # contract_amount = self.usdc_to_contract_amount(amount)
        # 
        # tx = self.contract.functions.depositEscrow(
        #     contract_claim_id,
        #     contract_amount
        # ).build_transaction({
        #     'from': from_address,
        #     'nonce': self.w3.eth.get_transaction_count(from_address),
        #     'gas': 200000,
        #     'gasPrice': self.w3.eth.gas_price
        # })
        
        # Mock for demo
        import hashlib
        mock_data = f"deposit-{claim_id}-{amount}"
        return "0x" + hashlib.sha256(mock_data.encode()).hexdigest()
    
    async def approve_claim(
        self,
        claim_id: str,
        amount: Decimal,
        recipient: str
    ) -> Optional[str]:
        """
        Approve a claim and transfer USDC to recipient.

        When AUTO_SETTLE_PRIVATE_KEY is set: runs USDC.approve, depositEscrow,
        approveClaim via web3. Otherwise returns a mock tx hash (for dev/tests).
        """
        amount_dec = Decimal(str(amount))

        # Mock when auto-settle key not configured
        if not self.auto_settle_private_key or not self.auto_settle_private_key.strip():
            import hashlib
            from datetime import datetime
            mock_data = f"approve-{claim_id}-{amount}-{recipient}-{datetime.utcnow().isoformat()}"
            return "0x" + hashlib.sha256(mock_data.encode()).hexdigest()

        # Cap: do not auto-settle if over AUTO_SETTLE_MAX_AMOUNT
        max_amt = os.getenv("AUTO_SETTLE_MAX_AMOUNT")
        if max_amt is not None and max_amt != "":
            try:
                if float(amount_dec) > float(max_amt):
                    logger.warning(
                        "approve_claim: amount %s exceeds AUTO_SETTLE_MAX_AMOUNT %s",
                        amount_dec, max_amt
                    )
                    return None
            except (ValueError, TypeError):
                pass

        try:
            from eth_account import Account

            w3 = Web3(HTTPProvider(self.rpc_url))
            if not w3.is_connected():
                logger.warning("approve_claim: RPC not connected %s", self.rpc_url)
                return None

            acct = Account.from_key(self.auto_settle_private_key)
            cid = arc_rpc.claim_id_to_uint256(claim_id)
            amount_6 = arc_rpc.usdc_to_contract_amount(amount_dec)

            if arc_rpc.is_settled(claim_id):
                logger.info("approve_claim: claim %s already settled", claim_id)
                return None

            balance = arc_rpc.get_escrow_balance(claim_id) or Decimal(0)
            if balance < amount_dec:
                # 1) USDC.approve(ClaimEscrow, amount_6)
                usdc = w3.eth.contract(
                    address=Web3.to_checksum_address(USDC_ADDRESS),
                    abi=USDC_ABI,
                )
                tx_approve = usdc.functions.approve(
                    Web3.to_checksum_address(CLAIM_ESCROW_ADDRESS), amount_6
                ).build_transaction({
                    "from": acct.address,
                    "nonce": w3.eth.get_transaction_count(acct.address),
                    "gas": 100_000,
                    "chainId": ARC_CHAIN_ID,
                })
                if "gasPrice" not in tx_approve:
                    tx_approve["gasPrice"] = w3.eth.gas_price
                signed = Account.sign_transaction(tx_approve, self.auto_settle_private_key)
                h = w3.eth.send_raw_transaction(signed.raw_transaction)
                w3.eth.wait_for_transaction_receipt(h, timeout=120)

                # 2) depositEscrow(claimId, amount_6)
                escrow = w3.eth.contract(
                    address=Web3.to_checksum_address(CLAIM_ESCROW_ADDRESS),
                    abi=CLAIM_ESCROW_ABI,
                )
                tx_dep = escrow.functions.depositEscrow(cid, amount_6).build_transaction({
                    "from": acct.address,
                    "nonce": w3.eth.get_transaction_count(acct.address),
                    "gas": 200_000,
                    "chainId": ARC_CHAIN_ID,
                })
                if "gasPrice" not in tx_dep:
                    tx_dep["gasPrice"] = w3.eth.gas_price
                signed_d = Account.sign_transaction(tx_dep, self.auto_settle_private_key)
                hd = w3.eth.send_raw_transaction(signed_d.raw_transaction)
                w3.eth.wait_for_transaction_receipt(hd, timeout=120)

            # 3) approveClaim(claimId, amount_6, recipient)
            escrow = w3.eth.contract(
                address=Web3.to_checksum_address(CLAIM_ESCROW_ADDRESS),
                abi=CLAIM_ESCROW_ABI,
            )
            tx_ac = escrow.functions.approveClaim(
                cid, amount_6, Web3.to_checksum_address(recipient)
            ).build_transaction({
                "from": acct.address,
                "nonce": w3.eth.get_transaction_count(acct.address),
                "gas": 200_000,
                "chainId": ARC_CHAIN_ID,
            })
            if "gasPrice" not in tx_ac:
                tx_ac["gasPrice"] = w3.eth.gas_price
            signed_ac = Account.sign_transaction(tx_ac, self.auto_settle_private_key)
            h_ac = w3.eth.send_raw_transaction(signed_ac.raw_transaction)
            w3.eth.wait_for_transaction_receipt(h_ac, timeout=120)
            return h_ac.hex()
        except Exception as e:
            logger.exception("approve_claim failed: %s", e)
            return None
    
    async def get_escrow_balance(self, claim_id: str) -> Decimal:
        """
        Get current escrow balance for a claim.
        
        Args:
            claim_id: Claim identifier
            
        Returns:
            Balance in USDC
        """
        # TODO: Implement actual blockchain call
        # contract_claim_id = self.claim_id_to_uint256(claim_id)
        # balance = self.contract.functions.getEscrowBalance(contract_claim_id).call()
        # return Decimal(balance) / Decimal("1000000")
        
        # Mock for demo
        return Decimal("0")
    
    async def is_settled(self, claim_id: str) -> bool:
        """
        Check if a claim has been settled.
        
        Args:
            claim_id: Claim identifier
            
        Returns:
            True if settled
        """
        # TODO: Implement actual blockchain call
        # contract_claim_id = self.claim_id_to_uint256(claim_id)
        # return self.contract.functions.isSettled(contract_claim_id).call()
        
        # Mock for demo
        return False


# Singleton instance
_blockchain_service: Optional[BlockchainService] = None


def get_blockchain_service() -> BlockchainService:
    """Get or create the blockchain service singleton."""
    global _blockchain_service
    if _blockchain_service is None:
        _blockchain_service = BlockchainService()
    return _blockchain_service
