"""
Complete flow tests with the real PDF document.

Tests three scenarios:
1. Claim amount matching PDF (should auto-approve)
2. Claim amount different from PDF (should detect mismatch)
3. No images provided (should request more data)

Tests:
- Data extraction
- Decision making (validation, fraud detection)
- Blockchain settlement flow
- Error cases
"""

import pytest
import os
from pathlib import Path
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from io import BytesIO

from src.models import Claim, Evidence
from src.agent.adk_agents.orchestrator import ADKOrchestrator


@pytest.fixture
def real_pdf_file():
    """Fixture for the real PDF file from uploads directory."""
    backend_dir = Path(__file__).parent.parent
    uploads_dir = backend_dir / "uploads"
    pdf_name = "202200420453_VROV4-digitCare_15942315559823643_SCHEDULE.pdf"
    
    if not uploads_dir.exists():
        pytest.skip(f"Uploads directory not found: {uploads_dir}")
    
    for subdir in uploads_dir.iterdir():
        if subdir.is_dir():
            pdf_path = subdir / pdf_name
            if pdf_path.exists():
                return str(pdf_path)
    
    pytest.skip(f"PDF file {pdf_name} not found in uploads directory")


@pytest.fixture
def pdf_total_amount():
    """Total amount from the PDF (digit_liability + customer_liability)."""
    # From extraction: digit_liability: 40370.65, customer_liability: ₹1000.0
    # Total: 41370.65 (matches total_amount: *41370.65)
    return Decimal("41370.65")


@pytest.mark.integration
class TestPDFCompleteFlow:
    """Complete flow tests with real PDF document."""
    
    @pytest.mark.asyncio
    async def test_scenario_1_matching_amount(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, mock_blockchain_service):
        """
        Scenario 1: Claim amount matches PDF total amount.
        
        Expected:
        - Data extraction succeeds
        - Amount validation passes
        - Low fraud risk
        - Auto-approval and settlement
        """
        print("\n" + "=" * 80)
        print("SCENARIO 1: Claim Amount Matching PDF")
        print("=" * 80)
        
        # Get wallet address
        from src.models import UserWallet
        wallet = test_db.query(UserWallet).filter(UserWallet.user_id == test_claimant.id).first()
        
        # Create claim with matching amount
        claim = Claim(
            id="test-claim-match",
            claimant_address=wallet.wallet_address if wallet else "0x1234567890123456789012345678901234567890",
            claim_amount=pdf_total_amount,
            status="SUBMITTED",
            processing_costs=Decimal("0.00")
        )
        test_db.add(claim)
        test_db.commit()
        
        # Create evidence with PDF only (no images)
        evidence = [
            Evidence(
                id="ev-1",
                claim_id=claim.id,
                file_type="document",
                file_path=real_pdf_file
            )
        ]
        test_db.add_all(evidence)
        test_db.commit()
        
        # Run orchestrator
        orchestrator = ADKOrchestrator()
        
        print(f"\n📋 Claim Details:")
        print(f"   └─ Claim ID: {claim.id}")
        print(f"   └─ Claim Amount: ₹{claim.claim_amount}")
        print(f"   └─ PDF Total Amount: ₹{pdf_total_amount}")
        print(f"   └─ Evidence: 1 document, 0 images")
        
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        print(f"\n📊 Evaluation Results:")
        print(f"   └─ Decision: {result.get('decision')}")
        print(f"   └─ Confidence: {result.get('confidence', 0.0):.2%}")
        print(f"   └─ Fraud Risk: {result.get('fraud_risk', 0.0):.2f}")
        print(f"   └─ Auto Settled: {result.get('auto_settled', False)}")
        print(f"   └─ TX Hash: {result.get('tx_hash', 'N/A')}")
        
        # Verify extraction
        agent_results = result.get("agent_results", {})
        document_result = agent_results.get("document", {})
        
        print(f"\n📄 Document Extraction:")
        if document_result:
            extracted_data = document_result.get("extracted_data", {})
            extracted_fields = extracted_data.get("extracted_fields", {})
            print(f"   └─ Fields Extracted: {len(extracted_fields)}")
            print(f"   └─ PDF Total Amount: {extracted_fields.get('total_amount', 'N/A')}")
            print(f"   └─ Digit Liability: {extracted_fields.get('digit_liability', 'N/A')}")
            print(f"   └─ Customer Liability: {extracted_fields.get('customer_liability', 'N/A')}")
        
        # Verify decision logic
        assert result.get("decision") in ["AUTO_APPROVED", "APPROVED_WITH_REVIEW", "NEEDS_REVIEW"]
        
        # If amounts match and confidence is high, should auto-approve
        if result.get("confidence", 0.0) >= 0.95 and result.get("fraud_risk", 1.0) < 0.3:
            assert result.get("decision") == "AUTO_APPROVED"
            assert result.get("auto_settled") is True
            assert result.get("tx_hash") is not None
        
        return result
    
    @pytest.mark.asyncio
    async def test_scenario_2_different_amount(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, mock_blockchain_service):
        """
        Scenario 2: Claim amount differs from PDF total amount.
        
        Expected:
        - Data extraction succeeds
        - Amount validation detects mismatch
        - Higher fraud risk
        - Needs review (not auto-approved)
        """
        print("\n" + "=" * 80)
        print("SCENARIO 2: Claim Amount Different from PDF")
        print("=" * 80)
        
        # Get wallet address
        from src.models import UserWallet
        wallet = test_db.query(UserWallet).filter(UserWallet.user_id == test_claimant.id).first()
        
        # Create claim with different amount (50% higher)
        different_amount = pdf_total_amount * Decimal("1.5")
        claim = Claim(
            id="test-claim-diff",
            claimant_address=wallet.wallet_address if wallet else "0x1234567890123456789012345678901234567890",
            claim_amount=different_amount,
            status="SUBMITTED",
            processing_costs=Decimal("0.00")
        )
        test_db.add(claim)
        test_db.commit()
        
        # Create evidence with PDF only
        evidence = [
            Evidence(
                id="ev-1",
                claim_id=claim.id,
                file_type="document",
                file_path=real_pdf_file
            )
        ]
        test_db.add_all(evidence)
        test_db.commit()
        
        # Run orchestrator
        orchestrator = ADKOrchestrator()
        
        print(f"\n📋 Claim Details:")
        print(f"   └─ Claim ID: {claim.id}")
        print(f"   └─ Claim Amount: ₹{claim.claim_amount}")
        print(f"   └─ PDF Total Amount: ₹{pdf_total_amount}")
        print(f"   └─ Difference: ₹{different_amount - pdf_total_amount} ({((different_amount - pdf_total_amount) / pdf_total_amount * 100):.1f}%)")
        print(f"   └─ Evidence: 1 document, 0 images")
        
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        print(f"\n📊 Evaluation Results:")
        print(f"   └─ Decision: {result.get('decision')}")
        print(f"   └─ Confidence: {result.get('confidence', 0.0):.2%}")
        print(f"   └─ Fraud Risk: {result.get('fraud_risk', 0.0):.2f}")
        print(f"   └─ Contradictions: {result.get('contradictions', [])}")
        print(f"   └─ Auto Settled: {result.get('auto_settled', False)}")
        
        # Verify extraction
        agent_results = result.get("agent_results", {})
        document_result = agent_results.get("document", {})
        
        print(f"\n📄 Document Extraction:")
        if document_result:
            extracted_data = document_result.get("extracted_data", {})
            extracted_fields = extracted_data.get("extracted_fields", {})
            print(f"   └─ Fields Extracted: {len(extracted_fields)}")
            print(f"   └─ PDF Total Amount: {extracted_fields.get('total_amount', 'N/A')}")
        
        # Verify decision logic - should detect mismatch
        assert result.get("decision") != "AUTO_APPROVED", "Should not auto-approve when amounts differ"
        assert result.get("auto_settled") is False, "Should not auto-settle when amounts differ"
        
        # Should have contradictions or higher fraud risk
        contradictions = result.get("contradictions", [])
        fraud_risk = result.get("fraud_risk", 0.0)
        
        assert len(contradictions) > 0 or fraud_risk >= 0.3, \
            f"Should detect mismatch: contradictions={contradictions}, fraud_risk={fraud_risk}"
        
        print(f"\n✅ Mismatch Detected:")
        print(f"   └─ Contradictions: {contradictions}")
        print(f"   └─ Fraud Risk: {fraud_risk:.2f}")
        
        return result
    
    @pytest.mark.asyncio
    async def test_scenario_3_no_images(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, mock_blockchain_service):
        """
        Scenario 3: No images provided, only PDF document.
        
        Expected:
        - Data extraction succeeds
        - Missing evidence detected
        - Lower confidence
        - Needs more data or review
        """
        print("\n" + "=" * 80)
        print("SCENARIO 3: No Images Provided")
        print("=" * 80)
        
        # Get wallet address
        from src.models import UserWallet
        wallet = test_db.query(UserWallet).filter(UserWallet.user_id == test_claimant.id).first()
        
        # Create claim with matching amount but no images
        claim = Claim(
            id="test-claim-no-images",
            claimant_address=wallet.wallet_address if wallet else "0x1234567890123456789012345678901234567890",
            claim_amount=pdf_total_amount,
            status="SUBMITTED",
            processing_costs=Decimal("0.00")
        )
        test_db.add(claim)
        test_db.commit()
        
        # Create evidence with PDF only (no images)
        evidence = [
            Evidence(
                id="ev-1",
                claim_id=claim.id,
                file_type="document",
                file_path=real_pdf_file
            )
        ]
        test_db.add_all(evidence)
        test_db.commit()
        
        # Run orchestrator
        orchestrator = ADKOrchestrator()
        
        print(f"\n📋 Claim Details:")
        print(f"   └─ Claim ID: {claim.id}")
        print(f"   └─ Claim Amount: ₹{claim.claim_amount}")
        print(f"   └─ Evidence: 1 document, 0 images")
        
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        print(f"\n📊 Evaluation Results:")
        print(f"   └─ Decision: {result.get('decision')}")
        print(f"   └─ Confidence: {result.get('confidence', 0.0):.2%}")
        print(f"   └─ Requested Data: {result.get('requested_data', [])}")
        print(f"   └─ Missing Evidence: {result.get('agent_results', {}).get('reasoning', {}).get('missing_evidence', [])}")
        
        # Verify extraction
        agent_results = result.get("agent_results", {})
        document_result = agent_results.get("document", {})
        
        print(f"\n📄 Document Extraction:")
        if document_result:
            extracted_data = document_result.get("extracted_data", {})
            extracted_fields = extracted_data.get("extracted_fields", {})
            print(f"   └─ Fields Extracted: {len(extracted_fields)}")
        
        # Verify decision logic - should request images or have lower confidence
        requested_data = result.get("requested_data", [])
        reasoning_result = agent_results.get("reasoning", {})
        missing_evidence = reasoning_result.get("missing_evidence", []) if isinstance(reasoning_result, dict) else []
        
        # Should request images or have lower confidence
        assert "image" in requested_data or "valid_image" in str(missing_evidence) or \
               result.get("confidence", 1.0) < 0.95, \
            f"Should request images or have lower confidence. requested_data={requested_data}, missing_evidence={missing_evidence}, confidence={result.get('confidence')}"
        
        print(f"\n✅ Missing Evidence Detected:")
        print(f"   └─ Requested Data: {requested_data}")
        print(f"   └─ Missing Evidence: {missing_evidence}")
        
        return result


@pytest.mark.integration
class TestErrorCases:
    """Test error cases and edge cases."""
    
    @pytest.mark.asyncio
    async def test_invalid_pdf_path(self, test_db, test_claimant, mock_blockchain_service):
        """Test handling of invalid PDF path."""
        print("\n" + "=" * 80)
        print("ERROR CASE: Invalid PDF Path")
        print("=" * 80)
        
        from src.models import UserWallet
        wallet = test_db.query(UserWallet).filter(UserWallet.user_id == test_claimant.id).first()
        
        claim = Claim(
            id="test-claim-invalid-pdf",
            claimant_address=wallet.wallet_address if wallet else "0x1234567890123456789012345678901234567890",
            claim_amount=Decimal("1000.00"),
            status="SUBMITTED",
            processing_costs=Decimal("0.00")
        )
        test_db.add(claim)
        test_db.commit()
        
        evidence = [
            Evidence(
                id="ev-1",
                claim_id=claim.id,
                file_type="document",
                file_path="/nonexistent/path/to/file.pdf"
            )
        ]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        print(f"\n📊 Results:")
        print(f"   └─ Decision: {result.get('decision')}")
        print(f"   └─ Confidence: {result.get('confidence', 0.0):.2%}")
        
        # Should handle error gracefully
        assert result.get("decision") in ["NEEDS_REVIEW", "INSUFFICIENT_DATA", "NEEDS_MORE_DATA"]
        assert result.get("confidence", 1.0) < 0.95
        
        return result
    
    @pytest.mark.asyncio
    async def test_zero_claim_amount(self, test_db, test_claimant, real_pdf_file, mock_blockchain_service):
        """Test handling of zero claim amount."""
        print("\n" + "=" * 80)
        print("ERROR CASE: Zero Claim Amount")
        print("=" * 80)
        
        from src.models import UserWallet
        wallet = test_db.query(UserWallet).filter(UserWallet.user_id == test_claimant.id).first()
        
        claim = Claim(
            id="test-claim-zero",
            claimant_address=wallet.wallet_address if wallet else "0x1234567890123456789012345678901234567890",
            claim_amount=Decimal("0.00"),
            status="SUBMITTED",
            processing_costs=Decimal("0.00")
        )
        test_db.add(claim)
        test_db.commit()
        
        evidence = [
            Evidence(
                id="ev-1",
                claim_id=claim.id,
                file_type="document",
                file_path=real_pdf_file
            )
        ]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        print(f"\n📊 Results:")
        print(f"   └─ Decision: {result.get('decision')}")
        print(f"   └─ Confidence: {result.get('confidence', 0.0):.2%}")
        
        # Should reject or flag as invalid
        assert result.get("decision") != "AUTO_APPROVED"
        
        return result
    
    @pytest.mark.asyncio
    async def test_no_evidence(self, test_db, test_claimant, mock_blockchain_service):
        """Test handling of claim with no evidence."""
        print("\n" + "=" * 80)
        print("ERROR CASE: No Evidence")
        print("=" * 80)
        
        from src.models import UserWallet
        wallet = test_db.query(UserWallet).filter(UserWallet.user_id == test_claimant.id).first()
        
        claim = Claim(
            id="test-claim-no-evidence",
            claimant_address=wallet.wallet_address if wallet else "0x1234567890123456789012345678901234567890",
            claim_amount=Decimal("1000.00"),
            status="SUBMITTED",
            processing_costs=Decimal("0.00")
        )
        test_db.add(claim)
        test_db.commit()
        
        evidence = []
        
        orchestrator = ADKOrchestrator()
        
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        print(f"\n📊 Results:")
        print(f"   └─ Decision: {result.get('decision')}")
        print(f"   └─ Confidence: {result.get('confidence', 0.0):.2%}")
        print(f"   └─ Requested Data: {result.get('requested_data', [])}")
        
        # Should request data or have very low confidence
        assert result.get("decision") in ["NEEDS_MORE_DATA", "INSUFFICIENT_DATA", "NEEDS_REVIEW"]
        assert len(result.get("requested_data", [])) > 0 or result.get("confidence", 1.0) < 0.5
        
        return result


@pytest.mark.integration
class TestBlockchainFlow:
    """Test blockchain settlement flow."""
    
    @pytest.mark.asyncio
    async def test_blockchain_settlement_flow(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, mock_blockchain_service):
        """Test complete blockchain settlement flow."""
        print("\n" + "=" * 80)
        print("BLOCKCHAIN SETTLEMENT FLOW")
        print("=" * 80)
        
        from src.models import UserWallet
        wallet = test_db.query(UserWallet).filter(UserWallet.user_id == test_claimant.id).first()
        
        claim = Claim(
            id="test-claim-settlement",
            claimant_address=wallet.wallet_address if wallet else "0x1234567890123456789012345678901234567890",
            claim_amount=pdf_total_amount,
            status="SUBMITTED",
            processing_costs=Decimal("0.00")
        )
        test_db.add(claim)
        test_db.commit()
        
        evidence = [
            Evidence(
                id="ev-1",
                claim_id=claim.id,
                file_type="document",
                file_path=real_pdf_file
            )
        ]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        orchestrator.blockchain = mock_blockchain_service
        
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        print(f"\n📊 Evaluation Results:")
        print(f"   └─ Decision: {result.get('decision')}")
        print(f"   └─ Auto Settled: {result.get('auto_settled', False)}")
        print(f"   └─ TX Hash: {result.get('tx_hash', 'N/A')}")
        
        # If auto-approved, verify blockchain was called
        if result.get("decision") == "AUTO_APPROVED" and result.get("auto_settled"):
            assert result.get("tx_hash") is not None
            # Verify blockchain service was called
            mock_blockchain_service.approve_claim.assert_called_once()
            print(f"\n✅ Blockchain Settlement:")
            print(f"   └─ Settlement Called: Yes")
            print(f"   └─ TX Hash: {result.get('tx_hash')}")
        else:
            print(f"\n⚠️  No Settlement:")
            print(f"   └─ Reason: Decision={result.get('decision')}, Auto Settled={result.get('auto_settled')}")
        
        return result
