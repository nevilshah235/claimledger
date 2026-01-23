"""
Arc RPC helper for read-only contract calls (eth_call).
Used for: usdc_allowance, get_escrow_balance.
No signing; no private keys.
"""

import logging
import os
from decimal import Decimal
from typing import Optional

from web3 import Web3

logger = logging.getLogger(__name__)

ARC_RPC_URL = os.getenv("ARC_RPC_URL", "https://rpc.testnet.arc.network")
USDC_ADDRESS = os.getenv("USDC_ADDRESS", "0x3600000000000000000000000000000000000000")
# Optional; EURC token contract on Arc. Used for the developer/auto-settle wallet's EURC balance.
EURC_ADDRESS = os.getenv("EURC_ADDRESS", "")
CLAIM_ESCROW_ADDRESS = os.getenv("CLAIM_ESCROW_ADDRESS", "0x80794995149E5d26F22c36eD56B817CBd8E5d4Fa")

# ERC-20 balanceOf ABI (shared by USDC, EURC)
ERC20_BALANCE_ABI = [
    {
        "name": "balanceOf",
        "type": "function",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
    },
]

# Minimal ABIs for eth_call
USDC_ABI = [
    {
        "name": "allowance",
        "type": "function",
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"},
        ],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
    },
    {
        "name": "balanceOf",
        "type": "function",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
    },
    {
        "name": "approve",
        "type": "function",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
    },
]

CLAIM_ESCROW_ABI = [
    {
        "name": "getEscrowBalance",
        "type": "function",
        "inputs": [{"name": "claimId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
    },
    {
        "name": "isSettled",
        "type": "function",
        "inputs": [{"name": "claimId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
    },
]


def _get_w3() -> Optional[Web3]:
    try:
        w3 = Web3(Web3.HTTPProvider(ARC_RPC_URL))
        if not w3.is_connected():
            logger.warning("Arc RPC not connected: %s", ARC_RPC_URL)
            return None
        return w3
    except Exception as e:
        logger.warning("Failed to connect to Arc RPC: %s", e)
        return None


def claim_id_to_uint256(claim_id: str) -> int:
    """Convert claim UUID to uint256 for contract. Uses first 8 bytes of UUID."""
    hex_str = claim_id.replace("-", "")[:16]
    return int(hex_str, 16)


def usdc_to_contract_amount(amount: Decimal) -> int:
    """Convert USDC amount to contract format (6 decimals). $1.00 = 1000000."""
    return int(amount * Decimal("1000000"))


def usdc_allowance(owner: str, spender: str) -> Optional[int]:
    """
    USDC.allowance(owner, spender) via eth_call.
    Returns raw 6-decimal units, or None on error.
    """
    w3 = _get_w3()
    if not w3:
        return None
    try:
        usdc = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS), abi=USDC_ABI
        )
        out = usdc.functions.allowance(
            Web3.to_checksum_address(owner), Web3.to_checksum_address(spender)
        ).call()
        return out
    except Exception as e:
        logger.warning("usdc_allowance failed: %s", e)
        return None


def get_escrow_balance(claim_id: str) -> Optional[Decimal]:
    """
    ClaimEscrow.getEscrowBalance(claimId) via eth_call.
    Returns USDC (human) or None on error.
    """
    w3 = _get_w3()
    if not w3:
        return None
    try:
        escrow = w3.eth.contract(
            address=Web3.to_checksum_address(CLAIM_ESCROW_ADDRESS),
            abi=CLAIM_ESCROW_ABI,
        )
        raw = escrow.functions.getEscrowBalance(claim_id_to_uint256(claim_id)).call()
        return Decimal(raw) / Decimal("1000000")
    except Exception as e:
        logger.warning("get_escrow_balance failed: %s", e)
        return None


def is_settled(claim_id: str) -> bool:
    """
    ClaimEscrow.isSettled(claimId) via eth_call.
    Returns True if the claim has been settled, False otherwise or on error.
    """
    w3 = _get_w3()
    if not w3:
        return False
    try:
        escrow = w3.eth.contract(
            address=Web3.to_checksum_address(CLAIM_ESCROW_ADDRESS),
            abi=CLAIM_ESCROW_ABI,
        )
        return bool(escrow.functions.isSettled(claim_id_to_uint256(claim_id)).call())
    except Exception as e:
        logger.warning("is_settled failed: %s", e)
        return False


def usdc_balance_of(address: str) -> Optional[Decimal]:
    """
    USDC.balanceOf(account) via eth_call.
    Returns human USDC (÷ 1e6) or None on error.
    """
    w3 = _get_w3()
    if not w3:
        return None
    try:
        usdc = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS), abi=USDC_ABI
        )
        raw = usdc.functions.balanceOf(Web3.to_checksum_address(address)).call()
        return Decimal(raw) / Decimal("1000000")
    except Exception as e:
        logger.warning("usdc_balance_of failed: %s", e)
        return None


def eurc_balance_of(address: str) -> Optional[Decimal]:
    """
    EURC.balanceOf(account) via eth_call.
    Returns human EURC (÷ 1e6, same as USDC) or None if EURC_ADDRESS not set or on error.
    """
    return None  # EURC commented out for now
    eurc_addr = (EURC_ADDRESS or "").strip()
    if not eurc_addr:
        return None
    w3 = _get_w3()
    if not w3:
        return None
    try:
        token = w3.eth.contract(
            address=Web3.to_checksum_address(eurc_addr), abi=ERC20_BALANCE_ABI
        )
        raw = token.functions.balanceOf(Web3.to_checksum_address(address)).call()
        return Decimal(raw) / Decimal("1000000")
    except Exception as e:
        logger.warning("eurc_balance_of failed: %s", e)
        return None


def get_balance_wei(address: str) -> Optional[int]:
    """
    Native (ARC) balance of an address via eth_getBalance.
    Returns balance in wei or None on error.
    """
    w3 = _get_w3()
    if not w3:
        return None
    try:
        return w3.eth.get_balance(Web3.to_checksum_address(address))
    except Exception as e:
        logger.warning("get_balance_wei failed: %s", e)
        return None


def get_transaction_status(tx_hash: str) -> Optional[dict]:
    """
    Get on-chain status of a transaction by hash.

    Uses eth_getTransactionByHash and eth_getTransactionReceipt.
    Returns None on RPC/connection error.

    Returns:
        {"status": "confirmed"|"pending"|"not_found"|"failed", "block_number": int|None}
    """
    if not tx_hash or not isinstance(tx_hash, str):
        return None
    tx_hash = tx_hash.strip()
    if not tx_hash.startswith("0x"):
        tx_hash = "0x" + tx_hash
    w3 = _get_w3()
    if not w3:
        return None
    try:
        tx = w3.eth.get_transaction(tx_hash)
        if tx is None:
            return {"status": "not_found", "block_number": None}
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        if receipt is None:
            return {"status": "pending", "block_number": None}
        # receipt.status: 0 = reverted/failed, 1 = success
        if receipt.get("status") == 1:
            return {"status": "confirmed", "block_number": receipt.get("blockNumber")}
        return {"status": "failed", "block_number": receipt.get("blockNumber")}
    except Exception as e:
        logger.warning("get_transaction_status failed for %s: %s", tx_hash[:18], e)
        return None


def get_gas_payment(tx_hash: str) -> Optional[dict]:
    """
    Get gas used and cost for a transaction (for settlement gas tracking).

    Uses eth_getTransactionByHash and eth_getTransactionReceipt.
    Returns None on RPC/connection error or if tx not found/pending.

    Returns:
        {
            "gas_used": int,
            "gas_price_wei": int,
            "cost_wei": int,
            "cost_arc": float,  # cost_wei / 1e18
        }
    """
    if not tx_hash or not isinstance(tx_hash, str):
        return None
    tx_hash = tx_hash.strip()
    if not tx_hash.startswith("0x"):
        tx_hash = "0x" + tx_hash
    w3 = _get_w3()
    if not w3:
        return None
    try:
        tx = w3.eth.get_transaction(tx_hash)
        if tx is None:
            return None
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        if receipt is None:
            return None  # Pending, no receipt yet
        gas_used = receipt.get("gasUsed")
        if gas_used is None:
            return None
        gas_used = int(gas_used)
        # EIP-1559: effectiveGasPrice; legacy: gasPrice on tx
        gas_price_wei = receipt.get("effectiveGasPrice") or tx.get("gasPrice") or 0
        gas_price_wei = int(gas_price_wei)
        cost_wei = gas_used * gas_price_wei
        cost_arc = float(cost_wei) / 1e18
        return {
            "gas_used": gas_used,
            "gas_price_wei": gas_price_wei,
            "cost_wei": cost_wei,
            "cost_arc": cost_arc,
        }
    except Exception as e:
        logger.warning("get_gas_payment failed for %s: %s", tx_hash[:18], e)
        return None
