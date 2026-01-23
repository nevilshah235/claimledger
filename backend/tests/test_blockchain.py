"""
Tests for blockchain settlement endpoints.

Settlement uses User-Controlled Circle wallets + ClaimEscrow:
- POST /blockchain/settle/{id}/challenge (step=approve|deposit|approve_claim)
- POST /blockchain/settle/{id}/complete

The legacy POST /blockchain/settle/{id} is deprecated and returns 400.
"""

import pytest
from decimal import Decimal
from fastapi import status
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_circle_and_rpc():
    """Mock CircleWalletsService and arc_rpc for /challenge and /complete."""
    with (
        patch("src.api.blockchain.CircleWalletsService") as MockCS,
        patch("src.api.blockchain.usdc_allowance", return_value=0),  # always do approve step
    ):
        mock_inst = MagicMock()
        mock_inst.validate_app_id = MagicMock(return_value=True)
        mock_inst.create_user_token = AsyncMock(
            return_value={"userToken": "ut", "encryptionKey": "ek"}
        )
        mock_inst.create_user_contract_execution_challenge = AsyncMock(
            return_value={"challengeId": "ch-123"}
        )
        mock_inst.get_user_transaction = AsyncMock(
            return_value={"state": "COMPLETED", "txHash": "0xabcdef1234567890"}
        )
        MockCS.return_value = mock_inst
        yield mock_inst


def test_settle_challenge_approve(client, test_db, test_claim, insurer_headers, insurer_wallet, mock_circle_and_rpc):
    """POST /challenge with step=approve returns challengeId, step, nextStep."""
    test_claim.status = "APPROVED"
    test_claim.approved_amount = Decimal("100.00")
    test_claim.claimant_address = "0x1234567890123456789012345678901234567890"
    test_db.commit()

    resp = client.post(
        f"/blockchain/settle/{test_claim.id}/challenge",
        headers=insurer_headers,
        json={"step": "approve"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["challengeId"] == "ch-123"
    assert data["step"] == "approve"
    assert data["nextStep"] == "deposit"
    assert "user_token" in data
    assert "encryption_key" in data


def test_settle_challenge_deposit(client, test_db, test_claim, insurer_headers, insurer_wallet, mock_circle_and_rpc):
    """POST /challenge with step=deposit returns challengeId, nextStep=approve_claim."""
    test_claim.status = "APPROVED"
    test_claim.approved_amount = Decimal("100.00")
    test_claim.claimant_address = "0x1234567890123456789012345678901234567890"
    test_db.commit()

    resp = client.post(
        f"/blockchain/settle/{test_claim.id}/challenge",
        headers=insurer_headers,
        json={"step": "deposit"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["challengeId"] == "ch-123"
    assert data["step"] == "deposit"
    assert data["nextStep"] == "approve_claim"


def test_settle_challenge_approve_claim(client, test_db, test_claim, insurer_headers, insurer_wallet, mock_circle_and_rpc):
    """POST /challenge with step=approve_claim returns nextStep=null."""
    test_claim.status = "APPROVED"
    test_claim.approved_amount = Decimal("100.00")
    test_claim.claimant_address = "0x1234567890123456789012345678901234567890"
    test_db.commit()

    resp = client.post(
        f"/blockchain/settle/{test_claim.id}/challenge",
        headers=insurer_headers,
        json={"step": "approve_claim"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["challengeId"] == "ch-123"
    assert data["step"] == "approve_claim"
    assert data["nextStep"] is None


def test_settle_challenge_claimant_address_invalid(client, test_db, test_claim, insurer_headers, insurer_wallet, mock_circle_and_rpc):
    """POST /challenge with invalid claimant_address returns 400."""
    test_claim.status = "APPROVED"
    test_claim.approved_amount = Decimal("100.00")
    test_claim.claimant_address = "invalid"
    test_db.commit()

    resp = client.post(
        f"/blockchain/settle/{test_claim.id}/challenge",
        headers=insurer_headers,
        json={"step": "approve"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "claimant" in resp.json()["detail"].lower() and "wallet" in resp.json()["detail"].lower()


def test_settle_challenge_admin_no_wallet(client, test_db, test_claim, insurer_headers):
    """POST /challenge when admin has no UserWallet returns 400. Do not use insurer_wallet fixture."""
    test_claim.status = "APPROVED"
    test_claim.approved_amount = Decimal("100.00")
    test_claim.claimant_address = "0x1234567890123456789012345678901234567890"
    test_db.commit()

    resp = client.post(
        f"/blockchain/settle/{test_claim.id}/challenge",
        headers=insurer_headers,
        json={"step": "approve"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "wallet" in resp.json()["detail"].lower()


def test_settle_complete_with_tx_hash(client, test_db, test_claim, insurer_headers, insurer_wallet):
    """POST /complete with transactionId and txHash sets SETTLED and returns tx_hash."""
    test_claim.status = "APPROVED"
    test_claim.approved_amount = Decimal("100.00")
    test_db.commit()

    resp = client.post(
        f"/blockchain/settle/{test_claim.id}/complete",
        headers=insurer_headers,
        json={"transactionId": "tx-456", "txHash": "0xsettled123"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["claim_id"] == test_claim.id
    assert data["tx_hash"] == "0xsettled123"
    assert data["status"] == "SETTLED"

    test_db.refresh(test_claim)
    assert test_claim.status == "SETTLED"
    assert test_claim.tx_hash == "0xsettled123"


def test_settle_complete_fetches_tx_hash_from_circle(client, test_db, test_claim, insurer_headers, insurer_wallet, mock_circle_and_rpc):
    """POST /complete with only transactionId fetches txHash from Circle when COMPLETED."""
    test_claim.status = "APPROVED"
    test_claim.approved_amount = Decimal("100.00")
    test_db.commit()

    resp = client.post(
        f"/blockchain/settle/{test_claim.id}/complete",
        headers=insurer_headers,
        json={"transactionId": "tx-789"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["tx_hash"] == "0xabcdef1234567890"
    assert data["status"] == "SETTLED"

    test_db.refresh(test_claim)
    assert test_claim.status == "SETTLED"
    assert test_claim.tx_hash == "0xabcdef1234567890"


# --- Legacy POST /settle/{id} is deprecated: expect 400 ---


def test_settle_claim_deprecated(client, test_db, test_claim, insurer_headers):
    """Legacy POST /blockchain/settle/{id} returns 400 (deprecated)."""
    test_claim.status = "APPROVED"
    test_claim.approved_amount = Decimal("1000.00")
    test_db.commit()

    resp = client.post(
        f"/blockchain/settle/{test_claim.id}",
        headers=insurer_headers,
        json={},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "deprecated" in resp.json()["detail"].lower()


def test_settle_claim_requires_insurer(client, test_db, test_claim, auth_headers):
    """Only insurers can call /challenge."""
    test_claim.status = "APPROVED"
    test_claim.approved_amount = Decimal("100.00")
    test_claim.claimant_address = "0x1234567890123456789012345678901234567890"
    test_db.commit()

    resp = client.post(
        f"/blockchain/settle/{test_claim.id}/challenge",
        headers=auth_headers,
        json={"step": "approve"},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert "insurer" in resp.json()["detail"].lower()


def test_settle_claim_requires_auth(client, test_db, test_claim):
    """Settlement /challenge requires authentication."""
    test_claim.status = "APPROVED"
    test_claim.approved_amount = Decimal("100.00")
    test_db.commit()

    resp = client.post(
        f"/blockchain/settle/{test_claim.id}/challenge",
        json={"step": "approve"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_settle_challenge_claim_not_approved(client, test_db, test_claim, insurer_headers, insurer_wallet, mock_circle_and_rpc):
    """POST /challenge requires claim in APPROVED status."""
    test_claim.status = "SUBMITTED"
    test_claim.approved_amount = Decimal("100.00")
    test_claim.claimant_address = "0x1234567890123456789012345678901234567890"
    test_db.commit()

    resp = client.post(
        f"/blockchain/settle/{test_claim.id}/challenge",
        headers=insurer_headers,
        json={"step": "approve"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "APPROVED" in resp.json()["detail"]


def test_get_transaction_status(client):
    """GET /blockchain/status/{tx_hash} returns on-chain status from Arc RPC."""
    tx_hash = "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    resp = client.get(f"/blockchain/status/{tx_hash}")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["tx_hash"] == tx_hash
    assert data["status"] in ("confirmed", "pending", "not_found", "failed", "unknown")
    assert "block_number" in data
    assert "explorer_url" in data
