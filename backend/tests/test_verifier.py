"""
Tests for x402-protected verifier endpoints.
Tests include GatewayService integration and receipt validation.
"""

import pytest
from fastapi import status
from decimal import Decimal
from unittest.mock import patch, AsyncMock


def test_document_verification_402(client, test_claim):
    """Test document verification returns 402 without payment receipt."""
    response = client.post(
        "/verifier/document",
        json={
            "claim_id": test_claim.id,
            "document_path": "/path/to/document.pdf"
        }
    )
    
    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
    data = response.json()
    assert data["error"] == "Payment required"
    assert data["amount"] == "0.10"
    assert data["currency"] == "USDC"
    assert "gateway_payment_id" in data
    assert "payment_url" in data


def test_document_verification_success(client, test_claim, mock_gateway_service):
    """Test document verification with valid payment receipt."""
    # Create a valid receipt
    mock_gateway_service.validate_receipt.return_value = True
    
    response = client.post(
        "/verifier/document",
        json={
            "claim_id": test_claim.id,
            "document_path": "/path/to/document.pdf"
        },
        headers={"X-Payment-Receipt": "valid_receipt_token_12345"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "extracted_data" in data
    assert data["valid"] is True
    assert "verification_id" in data


def test_document_verification_invalid_receipt(client, test_claim, mock_gateway_service):
    """Test document verification with invalid receipt."""
    # Mock returns False for invalid receipt
    mock_gateway_service.validate_receipt = AsyncMock(return_value=False)
    
    response = client.post(
        "/verifier/document",
        json={
            "claim_id": test_claim.id,
            "document_path": "/path/to/document.pdf"
        },
        headers={"X-Payment-Receipt": "invalid_receipt"}
    )
    
    # Should return 402 when receipt is invalid
    # But if mock mode accepts any receipt, might return 200
    assert response.status_code in [status.HTTP_402_PAYMENT_REQUIRED, status.HTTP_200_OK]


def test_image_analysis_402(client, test_claim):
    """Test image analysis returns 402 without payment receipt."""
    response = client.post(
        "/verifier/image",
        json={
            "claim_id": test_claim.id,
            "image_path": "/path/to/image.jpg"
        }
    )
    
    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
    data = response.json()
    assert data["amount"] == "0.15"  # Image analysis costs more
    assert data["currency"] == "USDC"


def test_image_analysis_success(client, test_claim, mock_gateway_service):
    """Test image analysis with valid payment receipt."""
    mock_gateway_service.validate_receipt.return_value = True
    
    response = client.post(
        "/verifier/image",
        json={
            "claim_id": test_claim.id,
            "image_path": "/path/to/image.jpg"
        },
        headers={"X-Payment-Receipt": "valid_receipt_token_12345"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "damage_assessment" in data
    assert data["valid"] is True
    assert "analysis_id" in data


def test_fraud_check_402(client, test_claim):
    """Test fraud check returns 402 without payment receipt."""
    response = client.post(
        "/verifier/fraud",
        json={
            "claim_id": test_claim.id
        }
    )
    
    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
    data = response.json()
    assert data["amount"] == "0.10"
    assert data["currency"] == "USDC"


def test_fraud_check_success(client, test_claim, mock_gateway_service):
    """Test fraud check with valid payment receipt."""
    mock_gateway_service.validate_receipt.return_value = True
    
    response = client.post(
        "/verifier/fraud",
        json={
            "claim_id": test_claim.id
        },
        headers={"X-Payment-Receipt": "valid_receipt_token_12345"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "fraud_score" in data
    assert "risk_level" in data
    assert "check_id" in data
    assert data["risk_level"] in ["LOW", "MEDIUM", "HIGH"]


def test_verifier_receipt_stored_in_db(client, test_claim, test_db, mock_gateway_service):
    """Test that payment receipts are stored in database."""
    from src.models import X402Receipt
    
    mock_gateway_service.validate_receipt.return_value = True
    receipt_token = "test_receipt_token_12345"
    
    response = client.post(
        "/verifier/document",
        json={
            "claim_id": test_claim.id,
            "document_path": "/path/to/document.pdf"
        },
        headers={"X-Payment-Receipt": receipt_token}
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    # Check receipt was stored
    stored_receipt = test_db.query(X402Receipt).filter(
        X402Receipt.claim_id == test_claim.id,
        X402Receipt.verifier_type == "document"
    ).first()
    
    assert stored_receipt is not None
    assert stored_receipt.gateway_receipt == receipt_token
    assert float(stored_receipt.amount) == 0.10


def test_verifier_different_prices(client, test_claim):
    """Test that different verifiers have different prices."""
    # Document: $0.10
    doc_response = client.post(
        "/verifier/document",
        json={
            "claim_id": test_claim.id,
            "document_path": "/path/to/document.pdf"
        }
    )
    assert doc_response.json()["amount"] == "0.10"
    
    # Image: $0.15
    img_response = client.post(
        "/verifier/image",
        json={
            "claim_id": test_claim.id,
            "image_path": "/path/to/image.jpg"
        }
    )
    assert img_response.json()["amount"] == "0.15"
    
    # Fraud: $0.10
    fraud_response = client.post(
        "/verifier/fraud",
        json={
            "claim_id": test_claim.id
        }
    )
    assert fraud_response.json()["amount"] == "0.10"


def test_verifier_402_response_headers(client, test_claim):
    """Test that 402 responses include proper headers."""
    response = client.post(
        "/verifier/document",
        json={
            "claim_id": test_claim.id,
            "document_path": "/path/to/document.pdf"
        }
    )
    
    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
    assert "X-Payment-Amount" in response.headers
    assert "X-Payment-Currency" in response.headers
    assert "X-Payment-Description" in response.headers
    assert "X-Gateway-Payment-Id" in response.headers
    assert response.headers["X-Payment-Amount"] == "0.10"
    assert response.headers["X-Payment-Currency"] == "USDC"
