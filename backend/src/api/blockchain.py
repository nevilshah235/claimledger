"""
Blockchain API endpoint.

Settlement uses User-Controlled Circle wallets + ClaimEscrow:
- POST /blockchain/settle/{claim_id}/challenge - Get a challenge for approve, deposit, or approve_claim step
- POST /blockchain/settle/{claim_id}/complete - Mark claim SETTLED after SDK execute

The legacy POST /blockchain/settle/{claim_id} is deprecated; use /challenge and /complete.
"""

import asyncio
import logging
import re
import uuid
from decimal import Decimal
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..database import get_db
from ..models import Claim, User, UserWallet
from ..services.gas_tracking import record_settlement_gas
from ..services.arc_rpc import (
    CLAIM_ESCROW_ADDRESS,
    USDC_ADDRESS,
    claim_id_to_uint256,
    get_transaction_status as arc_get_transaction_status,
    usdc_allowance,
    usdc_to_contract_amount,
)
from ..services.circle_wallets import CircleWalletsService

router = APIRouter(prefix="/blockchain", tags=["blockchain"])


def _raise_circle_error(e: httpx.HTTPStatusError, op: str) -> None:
    """Convert Circle/httpx errors to HTTPException so we return proper JSON (with CORS) instead of 500."""
    try:
        err = e.response.json()
        msg = err.get("message") or str(err.get("errors", err))
    except Exception:
        msg = e.response.text or str(e)
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Circle API error during {op} ({e.response.status_code}): {msg}",
    )


# Max uint256 for approve(ClaimEscrow, type(uint256).max)
MAX_UINT256 = "115792089237316195423570985008687907853269984665640564039457584007913129639935"


def _is_valid_eth_address(addr: Optional[str]) -> bool:
    return bool(
        addr
        and isinstance(addr, str)
        and addr.startswith("0x")
        and len(addr) == 42
        and re.match(r"^0x[0-9a-fA-F]{40}$", addr) is not None
    )


# --- Request/Response models ---


class SettleChallengeRequest(BaseModel):
    step: Literal["approve", "deposit", "approve_claim"] = Field(
        ..., description="Step: approve USDC, deposit to escrow, or approve_claim"
    )


class SettleChallengeResponse(BaseModel):
    challengeId: str
    user_token: Optional[str] = None
    encryption_key: Optional[str] = None
    step: str
    nextStep: Optional[str] = None


class SettleCompleteRequest(BaseModel):
    transactionId: str = Field(..., description="Circle transaction ID from last sdk.execute result")
    txHash: Optional[str] = Field(None, description="Optional; if not provided, fetched from Circle when COMPLETED")


class SettleCompleteResponse(BaseModel):
    claim_id: str
    tx_hash: str
    status: str = "SETTLED"


# --- Shared validation and helpers ---


def _validate_claim_for_settlement(claim: Claim, current_user: User, db: Session) -> UserWallet:
    if claim.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Claim must be APPROVED to settle. Current status: {claim.status}",
        )
    if not claim.approved_amount or claim.approved_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No approved amount set for this claim",
        )
    if not _is_valid_eth_address(claim.claimant_address):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Claimant has not connected a wallet. They must connect to receive the payout.",
        )
    user_wallet = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).first()
    if not user_wallet or not (user_wallet.circle_wallet_id and user_wallet.wallet_address):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your wallet is not set up. Complete Connect in your profile to settle.",
        )
    return user_wallet


# --- /challenge ---


@router.post("/settle/{claim_id}/challenge", response_model=SettleChallengeResponse)
async def settle_challenge(
    claim_id: str,
    body: SettleChallengeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a Circle contract-execution challenge for one step of settlement.

    Steps: approve (USDC.approve(ClaimEscrow)) -> deposit (depositEscrow) -> approve_claim.
    If RPC shows allowance already sufficient, approve is skipped and the deposit challenge is returned
    when step=approve.

    Returns challengeId for sdk.execute, and user_token/encryption_key for sdk.setAuthentication
    (typically needed on first challenge; can be omitted on later steps if client has them).
    """
    if current_user.role != "insurer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only insurers can settle claims",
        )
    try:
        uuid.UUID(claim_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid claim ID format")

    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    user_wallet = _validate_claim_for_settlement(claim, current_user, db)
    circle = CircleWalletsService()
    if not circle.validate_app_id():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Circle App ID is not configured. Settlement requires valid Circle setup.",
        )

    amount = Decimal(str(claim.approved_amount))
    amount_6 = usdc_to_contract_amount(amount)
    cid_u256 = claim_id_to_uint256(claim_id)
    wallet_id = user_wallet.circle_wallet_id
    admin_address = user_wallet.wallet_address
    claimant_address = claim.claimant_address

    # User token for SDK (and for get_user_transaction in /complete)
    try:
        token_data = await circle.create_user_token(str(current_user.id))
    except httpx.HTTPStatusError as e:
        _raise_circle_error(e, "create_user_token")

    user_token = token_data.get("userToken") or token_data.get("user_token")
    encryption_key = token_data.get("encryptionKey") or token_data.get("encryption_key")

    step = body.step

    # approve: optionally skip if allowance >= amount
    if step == "approve":
        allowance_val = usdc_allowance(admin_address, CLAIM_ESCROW_ADDRESS)
        if allowance_val is not None and allowance_val >= amount_6:
            # Skip approve; create and return deposit challenge
            try:
                ch = await circle.create_user_contract_execution_challenge(
                    user_token=user_token,
                    wallet_id=wallet_id,
                    contract_address=CLAIM_ESCROW_ADDRESS,
                    abi_function_signature="depositEscrow(uint256,uint256)",
                    abi_parameters=[str(cid_u256), str(amount_6)],
                    fee_level="MEDIUM",
                    blockchain="ARC-TESTNET",
                )
            except httpx.HTTPStatusError as e:
                _raise_circle_error(e, "contract_execution(deposit)")
            return SettleChallengeResponse(
                challengeId=ch["challengeId"],
                user_token=user_token,
                encryption_key=encryption_key,
                step="deposit",
                nextStep="approve_claim",
            )

        # Create approve challenge
        try:
            ch = await circle.create_user_contract_execution_challenge(
                user_token=user_token,
                wallet_id=wallet_id,
                contract_address=USDC_ADDRESS,
                abi_function_signature="approve(address,uint256)",
                abi_parameters=[CLAIM_ESCROW_ADDRESS, MAX_UINT256],
                fee_level="MEDIUM",
                blockchain="ARC-TESTNET",
            )
        except httpx.HTTPStatusError as e:
            _raise_circle_error(e, "contract_execution(approve)")
        return SettleChallengeResponse(
            challengeId=ch["challengeId"],
            user_token=user_token,
            encryption_key=encryption_key,
            step="approve",
            nextStep="deposit",
        )

    if step == "deposit":
        try:
            ch = await circle.create_user_contract_execution_challenge(
                user_token=user_token,
                wallet_id=wallet_id,
                contract_address=CLAIM_ESCROW_ADDRESS,
                abi_function_signature="depositEscrow(uint256,uint256)",
                abi_parameters=[str(cid_u256), str(amount_6)],
                fee_level="MEDIUM",
                blockchain="ARC-TESTNET",
            )
        except httpx.HTTPStatusError as e:
            _raise_circle_error(e, "contract_execution(deposit)")
        return SettleChallengeResponse(
            challengeId=ch["challengeId"],
            user_token=user_token,
            encryption_key=encryption_key,
            step="deposit",
            nextStep="approve_claim",
        )

    if step == "approve_claim":
        try:
            ch = await circle.create_user_contract_execution_challenge(
                user_token=user_token,
                wallet_id=wallet_id,
                contract_address=CLAIM_ESCROW_ADDRESS,
                abi_function_signature="approveClaim(uint256,uint256,address)",
                abi_parameters=[str(cid_u256), str(amount_6), claimant_address],
                fee_level="MEDIUM",
                blockchain="ARC-TESTNET",
            )
        except httpx.HTTPStatusError as e:
            _raise_circle_error(e, "contract_execution(approve_claim)")
        return SettleChallengeResponse(
            challengeId=ch["challengeId"],
            user_token=user_token,
            encryption_key=encryption_key,
            step="approve_claim",
            nextStep=None,
        )

    raise HTTPException(status_code=400, detail=f"Unexpected step: {step}")


# --- /latest-transaction (fallback when SDK execute does not return transactionId) ---


class LatestTransactionResponse(BaseModel):
    transactionId: str


@router.get("/settle/{claim_id}/latest-transaction", response_model=LatestTransactionResponse)
async def get_latest_settlement_transaction(
    claim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fallback: when the SDK execute callback does not return transactionId, the frontend
    can call this to get the most recent CONTRACT_EXECUTION transaction for the insurer's
    wallet. Use that id in settleComplete.

    Only for APPROVED claims; insurer-only.
    """
    if current_user.role != "insurer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only insurers can access this",
        )
    try:
        uuid.UUID(claim_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid claim ID format")
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Claim must be APPROVED. Current status: {claim.status}",
        )
    user_wallet = _validate_claim_for_settlement(claim, current_user, db)
    if not user_wallet.circle_wallet_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your wallet is not set up. Complete Connect in your profile.",
        )
    circle = CircleWalletsService()
    if not circle.validate_app_id() or not circle.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Circle is not configured",
        )
    try:
        token_data = await circle.create_user_token(str(current_user.id))
    except httpx.HTTPStatusError as e:
        _raise_circle_error(e, "create_user_token")
    user_token = token_data.get("userToken") or token_data.get("user_token")
    if not user_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not create user token for Circle",
        )
    try:
        txs = await circle.list_user_transactions(
            user_token=user_token,
            wallet_ids=[user_wallet.circle_wallet_id],
            operation="CONTRACT_EXECUTION",
            page_size=5,
        )
    except httpx.HTTPStatusError as e:
        _raise_circle_error(e, "list_user_transactions")
    if not txs:
        raise HTTPException(
            status_code=404,
            detail="No recent contract execution transaction found. Complete the 3 wallet steps first, or try again.",
        )
    first = txs[0]
    tid = first.get("id")
    if not tid:
        raise HTTPException(
            status_code=502,
            detail="Circle list transactions did not return transaction id",
        )
    return LatestTransactionResponse(transactionId=tid)


# --- /complete ---


@router.post("/settle/{claim_id}/complete", response_model=SettleCompleteResponse)
async def settle_complete(
    claim_id: str,
    body: SettleCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    After the client has run sdk.execute for the approve_claim challenge, call this with
    the Circle transactionId (and optional txHash). Resolves txHash from Circle if needed,
    then sets claim.status=SETTLED and claim.tx_hash.
    """
    if current_user.role != "insurer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only insurers can settle claims",
        )
    try:
        uuid.UUID(claim_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid claim ID format")

    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Claim must be APPROVED to complete settlement. Current status: {claim.status}",
        )

    tx_hash = body.txHash
    if not tx_hash:
        circle = CircleWalletsService()
        if not circle.api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Circle API is not configured; cannot resolve transaction.",
            )
        token_data = await circle.create_user_token(str(current_user.id))
        user_token = token_data.get("userToken") or token_data.get("user_token")

        # Poll Circle until transaction is COMPLETED, a terminal failure, or timeout.
        # Handles SENT/PENDING etc. without requiring the client to retry.
        tx: dict = {}
        max_attempts = 18
        poll_interval_seconds = 5.0
        terminal_failure_states = {"FAILED", "CANCELLED", "EXPIRED", "REJECTED"}
        _log = logging.getLogger(__name__)

        for attempt in range(max_attempts):
            try:
                tx = await circle.get_user_transaction(body.transactionId, user_token=user_token)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Could not fetch transaction from Circle: {e!s}",
                ) from e
            state = (tx.get("state") or tx.get("status") or "").upper()
            if state in ("COMPLETED", "COMPLETE"):
                break
            if state in terminal_failure_states:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Transaction ended in terminal state: {state}.",
                )
            _log.info(
                "Settlement tx %s state=%s, polling (attempt %s/%s)",
                body.transactionId,
                state,
                attempt + 1,
                max_attempts,
            )
            if attempt < max_attempts - 1:
                await asyncio.sleep(poll_interval_seconds)
        else:
            last_state = (tx.get("state") or tx.get("status") or "UNKNOWN") if tx else "UNKNOWN"
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail=f"Transaction not completed in time (last state={last_state}). You can retry with the same transactionId.",
            )

        tx_hash = tx.get("txHash") or tx.get("tx_hash")
        if not tx_hash:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Circle transaction is COMPLETED but no txHash in response.",
            )

    claim.status = "SETTLED"
    claim.tx_hash = tx_hash
    db.commit()

    try:
        record_settlement_gas(claim_id, tx_hash, db)
    except Exception as e:
        logging.getLogger(__name__).warning("Could not record settlement gas: %s", e)

    return SettleCompleteResponse(claim_id=claim_id, tx_hash=tx_hash, status="SETTLED")


# --- Legacy deprecated settle (kept for backwards compat; returns 400) ---


class SettlementRequest(BaseModel):
    recipient_override: Optional[str] = None


class SettlementResponse(BaseModel):
    claim_id: str
    tx_hash: str
    amount: float
    recipient: str
    status: str


@router.post("/settle/{claim_id}", response_model=SettlementResponse, deprecated=True)
async def settle_claim(
    claim_id: str,
    request: SettlementRequest = SettlementRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deprecated. Use POST /blockchain/settle/{id}/challenge and POST /blockchain/settle/{id}/complete
    for real USDC settlement via User-Controlled wallets and ClaimEscrow.
    """
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="This endpoint is deprecated. Use POST /blockchain/settle/{id}/challenge and POST /blockchain/settle/{id}/complete for real USDC settlement.",
    )


@router.get("/status/{tx_hash}")
async def get_transaction_status(tx_hash: str):
    """
    Get on-chain status of a settlement transaction.

    Queries Arc RPC (eth_getTransactionByHash, eth_getTransactionReceipt).
    status: confirmed | pending | not_found | failed | unknown (RPC error).
    """
    res = arc_get_transaction_status(tx_hash)
    if res is None:
        return {
            "tx_hash": tx_hash,
            "status": "unknown",
            "block_number": None,
            "explorer_url": f"https://testnet.arcscan.app/tx/{tx_hash}",
        }
    return {
        "tx_hash": tx_hash,
        "status": res["status"],
        "block_number": res.get("block_number"),
        "explorer_url": f"https://testnet.arcscan.app/tx/{tx_hash}",
    }
