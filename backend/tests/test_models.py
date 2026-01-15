"""
Tests for database models.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from src.models import User, UserWallet, Claim, Evidence, Evaluation, X402Receipt


def test_claim_model(test_db):
    """Test Claim model creation."""
    claim = Claim(
        id="test-claim-1",
        claimant_address="0x1234567890123456789012345678901234567890",
        claim_amount=Decimal("1500.00"),
        status="SUBMITTED",
        processing_costs=Decimal("0.00")
    )
    test_db.add(claim)
    test_db.commit()
    
    retrieved = test_db.query(Claim).filter(Claim.id == "test-claim-1").first()
    assert retrieved is not None
    assert retrieved.claimant_address == "0x1234567890123456789012345678901234567890"
    assert float(retrieved.claim_amount) == 1500.00
    assert retrieved.status == "SUBMITTED"


def test_evidence_model(test_db, test_claim):
    """Test Evidence model and relationship with Claim."""
    evidence = Evidence(
        id="test-evidence-1",
        claim_id=test_claim.id,
        file_type="image",
        file_path="/uploads/test-image.jpg"
    )
    test_db.add(evidence)
    test_db.commit()
    
    retrieved = test_db.query(Evidence).filter(Evidence.id == "test-evidence-1").first()
    assert retrieved is not None
    assert retrieved.claim_id == test_claim.id
    assert retrieved.file_type == "image"
    assert retrieved.claim.id == test_claim.id  # Relationship works


def test_user_model(test_db):
    """Test User model creation."""
    from src.services.auth import get_password_hash
    
    user = User(
        id="test-user-1",
        email="testuser@example.com",
        password_hash=get_password_hash("password123"),
        role="claimant"
    )
    test_db.add(user)
    test_db.commit()
    
    retrieved = test_db.query(User).filter(User.id == "test-user-1").first()
    assert retrieved is not None
    assert retrieved.email == "testuser@example.com"
    assert retrieved.role == "claimant"


def test_user_wallet_model(test_db, test_user):
    """Test UserWallet model and relationship with User."""
    wallet = UserWallet(
        user_id=test_user.id,
        wallet_address="0x9876543210987654321098765432109876543210",
        circle_wallet_id="circle-wallet-123",
        wallet_set_id="wallet-set-456"
    )
    test_db.add(wallet)
    test_db.commit()
    
    retrieved = test_db.query(UserWallet).filter(UserWallet.user_id == test_user.id).first()
    assert retrieved is not None
    assert retrieved.wallet_address == "0x9876543210987654321098765432109876543210"
    assert retrieved.user.id == test_user.id  # Relationship works


def test_evaluation_model(test_db, test_claim):
    """Test Evaluation model and relationship with Claim."""
    evaluation = Evaluation(
        id="test-eval-1",
        claim_id=test_claim.id,
        reasoning="Test reasoning for claim evaluation"
    )
    test_db.add(evaluation)
    test_db.commit()
    
    retrieved = test_db.query(Evaluation).filter(Evaluation.id == "test-eval-1").first()
    assert retrieved is not None
    assert retrieved.claim_id == test_claim.id
    assert retrieved.reasoning == "Test reasoning for claim evaluation"
    assert retrieved.claim.id == test_claim.id  # Relationship works


def test_x402_receipt_model(test_db, test_claim):
    """Test X402Receipt model and relationship with Claim."""
    receipt = X402Receipt(
        id="test-receipt-1",
        claim_id=test_claim.id,
        verifier_type="document",
        amount=Decimal("0.10"),
        gateway_payment_id="payment-123",
        gateway_receipt="receipt-token-456"
    )
    test_db.add(receipt)
    test_db.commit()
    
    retrieved = test_db.query(X402Receipt).filter(X402Receipt.id == "test-receipt-1").first()
    assert retrieved is not None
    assert retrieved.claim_id == test_claim.id
    assert retrieved.verifier_type == "document"
    assert float(retrieved.amount) == 0.10
    assert retrieved.claim.id == test_claim.id  # Relationship works


def test_claim_evidence_cascade(test_db, test_claim):
    """Test that deleting a claim cascades to evidence."""
    evidence = Evidence(
        id="test-evidence-cascade",
        claim_id=test_claim.id,
        file_type="document",
        file_path="/test/path.pdf"
    )
    test_db.add(evidence)
    test_db.commit()
    
    # Delete claim
    test_db.delete(test_claim)
    test_db.commit()
    
    # Evidence should be deleted
    retrieved = test_db.query(Evidence).filter(Evidence.id == "test-evidence-cascade").first()
    assert retrieved is None


def test_claim_evaluations_cascade(test_db, test_claim):
    """Test that deleting a claim cascades to evaluations."""
    evaluation = Evaluation(
        id="test-eval-cascade",
        claim_id=test_claim.id,
        reasoning="Test"
    )
    test_db.add(evaluation)
    test_db.commit()
    
    # Delete claim
    test_db.delete(test_claim)
    test_db.commit()
    
    # Evaluation should be deleted
    retrieved = test_db.query(Evaluation).filter(Evaluation.id == "test-eval-cascade").first()
    assert retrieved is None


def test_claim_x402_receipts_cascade(test_db, test_claim):
    """Test that deleting a claim cascades to x402 receipts."""
    receipt = X402Receipt(
        id="test-receipt-cascade",
        claim_id=test_claim.id,
        verifier_type="document",
        amount=Decimal("0.10"),
        gateway_payment_id="payment-123",
        gateway_receipt="receipt-456"
    )
    test_db.add(receipt)
    test_db.commit()
    
    # Delete claim
    test_db.delete(test_claim)
    test_db.commit()
    
    # Receipt should be deleted
    retrieved = test_db.query(X402Receipt).filter(X402Receipt.id == "test-receipt-cascade").first()
    assert retrieved is None
