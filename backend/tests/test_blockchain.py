"""
Tests for blockchain settlement endpoints.
"""

import pytest
from fastapi import status
from decimal import Decimal


def test_settle_claim(client, test_db, test_claim, insurer_headers, mock_blockchain_service):
    """Test settling an approved claim."""
    # Set claim to APPROVED status
    test_claim.status = "APPROVED"
    test_claim.approved_amount = Decimal("1000.00")
    test_claim.decision = "APPROVED"
    test_db.commit()
    
    response = client.post(
        f"/blockchain/settle/{test_claim.id}",
        headers=insurer_headers,
        json={}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["claim_id"] == test_claim.id
    assert "tx_hash" in data
    assert data["status"] == "SETTLED"
    assert float(data["amount"]) == 1000.00


def test_settle_claim_requires_insurer(client, test_db, test_claim, auth_headers):
    """Test that only insurers can settle claims."""
    # Set claim to APPROVED
    test_claim.status = "APPROVED"
    test_claim.approved_amount = Decimal("1000.00")
    test_db.commit()
    
    response = client.post(
        f"/blockchain/settle/{test_claim.id}",
        headers=auth_headers,  # Claimant headers
        json={}
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "insurer" in response.json()["detail"].lower()


def test_settle_claim_requires_auth(client, test_db, test_claim):
    """Test that settlement requires authentication."""
    test_claim.status = "APPROVED"
    test_claim.approved_amount = Decimal("1000.00")
    test_db.commit()
    
    response = client.post(
        f"/blockchain/settle/{test_claim.id}",
        json={}
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_settle_claim_not_approved(client, test_db, test_claim, insurer_headers):
    """Test that only APPROVED claims can be settled."""
    # Claim is in SUBMITTED status
    assert test_claim.status == "SUBMITTED"
    
    response = client.post(
        f"/blockchain/settle/{test_claim.id}",
        headers=insurer_headers,
        json={}
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "APPROVED" in response.json()["detail"]


def test_settle_claim_no_approved_amount(client, test_db, test_claim, insurer_headers):
    """Test that claim must have approved_amount set."""
    test_claim.status = "APPROVED"
    test_claim.approved_amount = None
    test_db.commit()
    
    response = client.post(
        f"/blockchain/settle/{test_claim.id}",
        headers=insurer_headers,
        json={}
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "approved amount" in response.json()["detail"].lower()


def test_settle_claim_updates_status(client, test_db, test_claim, insurer_headers, mock_blockchain_service):
    """Test that settlement updates claim status to SETTLED."""
    test_claim.status = "APPROVED"
    test_claim.approved_amount = Decimal("1000.00")
    test_db.commit()
    
    response = client.post(
        f"/blockchain/settle/{test_claim.id}",
        headers=insurer_headers,
        json={}
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    # Refresh from database
    test_db.refresh(test_claim)
    assert test_claim.status == "SETTLED"
    assert test_claim.tx_hash is not None


def test_settle_claim_with_recipient_override(client, test_db, test_claim, insurer_headers, mock_blockchain_service):
    """Test settlement with custom recipient address."""
    test_claim.status = "APPROVED"
    test_claim.approved_amount = Decimal("1000.00")
    test_db.commit()
    
    custom_recipient = "0x9876543210987654321098765432109876543210"
    
    response = client.post(
        f"/blockchain/settle/{test_claim.id}",
        headers=insurer_headers,
        json={"recipient_override": custom_recipient}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["recipient"] == custom_recipient


def test_get_transaction_status(client, mock_blockchain_service):
    """Test getting transaction status."""
    tx_hash = "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    
    response = client.get(f"/blockchain/status/{tx_hash}")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["tx_hash"] == tx_hash
    assert "status" in data
    assert "block_number" in data
    assert "explorer_url" in data
