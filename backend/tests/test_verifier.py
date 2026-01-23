"""
Tests for verifier endpoints. Evaluations are free; X-Internal-Secret required.
"""

import pytest
from fastapi import status
from unittest.mock import patch, AsyncMock


# Default matches verifier and verifier_client when EVALUATION_INTERNAL_SECRET is unset
INTERNAL_SECRET = "dev-internal-secret"
HEADERS = {"X-Internal-Secret": INTERNAL_SECRET}


def test_document_verification_401_without_secret(client, test_claim):
    """Without X-Internal-Secret, verifier returns 401."""
    response = client.post(
        "/verifier/document",
        json={"claim_id": test_claim.id, "document_path": "/path/to/document.pdf"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@patch("src.api.verifier.ADKDocumentAgent")
def test_document_verification_success(mock_doc_agent, client, test_claim):
    """With X-Internal-Secret and mocked agent, document verification returns 200."""
    mock_doc_agent.return_value.analyze = AsyncMock(
        return_value={"extracted_data": {"amount": 500}, "valid": True, "verification_id": "v1"}
    )
    response = client.post(
        "/verifier/document",
        json={"claim_id": test_claim.id, "document_path": "/path/to/doc.pdf"},
        headers=HEADERS,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "extracted_data" in data
    assert data["valid"] is True
    assert "verification_id" in data


def test_image_analysis_401_without_secret(client, test_claim):
    """Without X-Internal-Secret, image verifier returns 401."""
    response = client.post(
        "/verifier/image",
        json={"claim_id": test_claim.id, "image_path": "/path/to/img.jpg"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@patch("src.api.verifier.ADKImageAgent")
def test_image_analysis_success(mock_img_agent, client, test_claim):
    """With X-Internal-Secret and mocked agent, image analysis returns 200."""
    mock_img_agent.return_value.analyze = AsyncMock(
        return_value={"damage_assessment": {"severity": "low"}, "valid": True, "analysis_id": "a1"}
    )
    response = client.post(
        "/verifier/image",
        json={"claim_id": test_claim.id, "image_path": "/path/to/img.jpg"},
        headers=HEADERS,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "damage_assessment" in data
    assert data["valid"] is True
    assert "analysis_id" in data


def test_fraud_check_401_without_secret(client, test_claim):
    """Without X-Internal-Secret, fraud verifier returns 401."""
    response = client.post(
        "/verifier/fraud",
        json={"claim_id": test_claim.id},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@patch("src.api.verifier.ADKFraudAgent")
def test_fraud_check_success(mock_fraud_agent, client, test_claim):
    """With X-Internal-Secret and mocked agent, fraud check returns 200."""
    mock_fraud_agent.return_value.analyze = AsyncMock(
        return_value={"fraud_score": 0.1, "risk_level": "LOW", "check_id": "f1"}
    )
    response = client.post(
        "/verifier/fraud",
        json={"claim_id": test_claim.id},
        headers=HEADERS,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "fraud_score" in data
    assert "risk_level" in data
    assert "check_id" in data


@patch("src.api.verifier.ADKDocumentAgent")
def test_verifier_usage_stored(mock_doc_agent, client, test_claim, test_db):
    """Verifier stores X402Receipt with amount=0 (evaluations free)."""
    from src.models import X402Receipt

    mock_doc_agent.return_value.analyze = AsyncMock(return_value={"extracted_data": {}, "valid": True, "verification_id": "v1"})
    response = client.post(
        "/verifier/document",
        json={"claim_id": test_claim.id, "document_path": "/path/to/doc.pdf"},
        headers=HEADERS,
    )
    assert response.status_code == status.HTTP_200_OK

    rec = test_db.query(X402Receipt).filter(X402Receipt.claim_id == test_claim.id, X402Receipt.verifier_type == "document").first()
    assert rec is not None
    assert float(rec.amount) == 0.0
    assert rec.gateway_receipt == "free"
