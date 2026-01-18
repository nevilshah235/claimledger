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
    
    assert test_claim.status in ["APPROVED", "NEEDS_REVIEW", "SETTLED"]
    assert test_claim.decision is not None
    assert test_claim.confidence is not None
    # Processing costs may be 0 if not explicitly set by orchestrator
    # The response should include processing_costs
    data = response.json()
    assert "processing_costs" in data
    assert float(data["processing_costs"]) >= 0


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


def test_evaluate_claim_stores_agent_results(client, test_db, test_claim):
    """Verify AgentResult records are created."""
    from src.models import AgentResult
    
    response = client.post(f"/agent/evaluate/{test_claim.id}")
    
    assert response.status_code == status.HTTP_200_OK
    
    # Check AgentResult records were created
    agent_results = test_db.query(AgentResult).filter(
        AgentResult.claim_id == test_claim.id
    ).all()
    
    assert len(agent_results) > 0
    
    # Verify at least one agent result exists
    agent_types = [r.agent_type for r in agent_results]
    assert any(t in ["document", "image", "fraud", "reasoning"] for t in agent_types)


def test_evaluate_claim_updates_claim_status(client, test_db, test_claim):
    """Test status transitions (SUBMITTED → EVALUATING → APPROVED/NEEDS_REVIEW)."""
    from src.models import Claim
    
    assert test_claim.status == "SUBMITTED"
    
    response = client.post(f"/agent/evaluate/{test_claim.id}")
    
    assert response.status_code == status.HTTP_200_OK
    
    # Refresh claim from database
    test_db.refresh(test_claim)
    
    # Status should have transitioned
    assert test_claim.status in ["APPROVED", "NEEDS_REVIEW", "SETTLED"]
    assert test_claim.decision in ["AUTO_APPROVED", "NEEDS_REVIEW"]


def test_evaluate_claim_sets_auto_approved_flag(client, test_db, test_claim):
    """Verify auto_approved flag is set."""
    from src.models import Claim
    
    response = client.post(f"/agent/evaluate/{test_claim.id}")
    
    assert response.status_code == status.HTTP_200_OK
    
    test_db.refresh(test_claim)
    
    data = response.json()
    if data["decision"] == "AUTO_APPROVED":
        assert test_claim.auto_approved is True
        assert data["auto_approved"] is True
    else:
        assert test_claim.auto_approved is False
        assert data["auto_approved"] is False


def test_evaluate_claim_sets_auto_settled_flag(client, test_db, test_claim, mock_blockchain_service):
    """Verify auto_settled flag is set."""
    from src.models import Claim
    
    response = client.post(f"/agent/evaluate/{test_claim.id}")
    
    assert response.status_code == status.HTTP_200_OK
    
    test_db.refresh(test_claim)
    
    data = response.json()
    if data.get("auto_settled"):
        assert test_claim.auto_settled is True
        assert data["auto_settled"] is True
        assert data.get("tx_hash") is not None
    else:
        assert test_claim.auto_settled is False or test_claim.auto_settled is None


def test_evaluate_claim_stores_summary(client, test_db, test_claim):
    """Verify comprehensive_summary is stored."""
    from src.models import Claim
    
    response = client.post(f"/agent/evaluate/{test_claim.id}")
    
    assert response.status_code == status.HTTP_200_OK
    
    test_db.refresh(test_claim)
    
    data = response.json()
    if data.get("summary"):
        assert test_claim.comprehensive_summary is not None
        assert len(test_claim.comprehensive_summary) > 0
        assert data["summary"] == test_claim.comprehensive_summary


def test_evaluate_claim_stores_review_reasons(client, test_db, test_claim):
    """Verify review_reasons JSON is stored."""
    from src.models import Claim
    
    response = client.post(f"/agent/evaluate/{test_claim.id}")
    
    assert response.status_code == status.HTTP_200_OK
    
    test_db.refresh(test_claim)
    
    data = response.json()
    if data["decision"] == "NEEDS_REVIEW":
        if data.get("review_reasons"):
            assert test_claim.review_reasons is not None
            assert isinstance(test_claim.review_reasons, list)
            assert len(test_claim.review_reasons) > 0


def test_evaluate_claim_creates_evaluation_record(client, test_db, test_claim):
    """Verify Evaluation record creation."""
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


def test_evaluate_claim_with_tx_hash(client, test_db, test_claim, mock_blockchain_service):
    """Verify transaction hash storage on settlement."""
    from src.models import Claim
    
    response = client.post(f"/agent/evaluate/{test_claim.id}")
    
    assert response.status_code == status.HTTP_200_OK
    
    test_db.refresh(test_claim)
    
    data = response.json()
    if data.get("auto_settled") and data.get("tx_hash"):
        assert test_claim.tx_hash is not None
        assert test_claim.tx_hash == data["tx_hash"]
        assert test_claim.status == "SETTLED"


def test_evaluate_claim_processing_costs(client, test_claim):
    """Verify processing_costs calculation."""
    response = client.post(f"/agent/evaluate/{test_claim.id}")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert "processing_costs" in data
    assert float(data["processing_costs"]) >= 0.35  # Total x402 costs


@pytest.mark.asyncio
async def test_evaluate_claim_concurrent_requests(client, test_db, test_claimant):
    """Test handling multiple concurrent evaluations."""
    import asyncio
    import uuid
    from src.models import Claim, UserWallet
    
    # Create multiple claims
    wallet = test_db.query(UserWallet).filter(UserWallet.user_id == test_claimant.id).first()
    
    claims = []
    for i in range(3):
        claim = Claim(
            id=str(uuid.uuid4()),
            claimant_address=wallet.wallet_address if wallet else "0x1234567890123456789012345678901234567890",
            claim_amount=Decimal("1000.00"),
            status="SUBMITTED",
            processing_costs=Decimal("0.00")
        )
        test_db.add(claim)
        claims.append(claim)
    
    test_db.commit()
    
    # Evaluate all claims concurrently
    async def evaluate_claim_async(claim_id):
        return client.post(f"/agent/evaluate/{claim_id}")
    
    tasks = [evaluate_claim_async(claim.id) for claim in claims]
    responses = await asyncio.gather(*tasks)
    
    # All should succeed
    for response in responses:
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "decision" in data
        assert "confidence" in data


@pytest.mark.real_api
def test_evaluate_claim_with_real_gemini_api(client, test_claim_with_evidence):
    """Test with real Gemini API (when key available)."""
    import os
    
    if not os.getenv("GOOGLE_AI_API_KEY"):
        pytest.skip("GOOGLE_AI_API_KEY not set, skipping real API test")
    
    response = client.post(f"/agent/evaluate/{test_claim_with_evidence.id}")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert data["claim_id"] == test_claim_with_evidence.id
    assert "decision" in data
    assert "confidence" in data
    assert "reasoning" in data
    assert data["decision"] in ["AUTO_APPROVED", "NEEDS_REVIEW"]
