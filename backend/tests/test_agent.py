"""
Tests for agent evaluation endpoints.
"""

import pytest
from fastapi import status
from decimal import Decimal


def test_evaluate_claim(client, test_claim):
    """Test evaluating a claim."""
    # Note: Agent endpoint doesn't require auth in current implementation
    response = client.post(f"/agent/evaluate/{test_claim.id}")
    
    # Should return 200 for SUBMITTED claim
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["claim_id"] == test_claim.id
    assert "decision" in data
    assert "confidence" in data
    assert "reasoning" in data
    assert "processing_costs" in data
    assert data["decision"] in ["APPROVED", "NEEDS_REVIEW", "REJECTED"]


def test_evaluate_claim_not_found(client):
    """Test evaluating a non-existent claim."""
    import uuid
    fake_id = str(uuid.uuid4())
    response = client.post(f"/agent/evaluate/{fake_id}")
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_evaluate_claim_invalid_id(client):
    """Test evaluating a claim with invalid ID format."""
    response = client.post("/agent/evaluate/invalid-id-format")
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_evaluate_claim_wrong_status(client, test_db, test_claim):
    """Test that claims in wrong status cannot be evaluated."""
    from src.models import Claim
    
    # Set claim to SETTLED status
    test_claim.status = "SETTLED"
    test_db.commit()
    
    response = client.post(f"/agent/evaluate/{test_claim.id}")
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "status" in response.json()["detail"].lower()


def test_evaluation_updates_claim(client, test_db, test_claim):
    """Test that evaluation updates claim status and fields."""
    from src.models import Claim
    
    assert test_claim.status == "SUBMITTED"
    assert test_claim.decision is None
    assert test_claim.confidence is None
    
    response = client.post(f"/agent/evaluate/{test_claim.id}")
    
    assert response.status_code == status.HTTP_200_OK
    
    # Refresh claim from database
    test_db.refresh(test_claim)
    
    assert test_claim.status in ["APPROVED", "NEEDS_REVIEW"]
    assert test_claim.decision is not None
    assert test_claim.confidence is not None
    assert test_claim.processing_costs > 0


def test_evaluation_creates_evaluation_record(client, test_db, test_claim):
    """Test that evaluation creates an Evaluation record."""
    from src.models import Evaluation
    
    response = client.post(f"/agent/evaluate/{test_claim.id}")
    
    assert response.status_code == status.HTTP_200_OK
    
    # Check Evaluation record was created
    evaluation = test_db.query(Evaluation).filter(
        Evaluation.claim_id == test_claim.id
    ).first()
    
    assert evaluation is not None
    assert evaluation.reasoning is not None
    assert len(evaluation.reasoning) > 0


def test_evaluation_processing_costs(client, test_claim):
    """Test that evaluation includes processing costs."""
    response = client.post(f"/agent/evaluate/{test_claim.id}")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "processing_costs" in data
    assert float(data["processing_costs"]) > 0
    # Should be sum of x402 payments (0.10 + 0.15 + 0.10 = 0.35)
    assert float(data["processing_costs"]) >= 0.35


def test_evaluation_approved_status(client, test_db, test_claim):
    """Test that high confidence leads to APPROVED status."""
    response = client.post(f"/agent/evaluate/{test_claim.id}")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    test_db.refresh(test_claim)
    
    if data["confidence"] >= 0.85:
        assert data["decision"] == "APPROVED"
        assert test_claim.status == "APPROVED"
        assert test_claim.approved_amount is not None
    else:
        assert data["decision"] == "NEEDS_REVIEW"
        assert test_claim.status == "NEEDS_REVIEW"
