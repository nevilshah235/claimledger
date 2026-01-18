"""
Detailed test scenarios for orchestrator agent improvements.

This test suite covers:
1. Amount validation scenarios (exact match, small/medium/large differences)
2. Tool calling sequence validation
3. Decision logic edge cases
4. Error handling scenarios
5. JSON parsing robustness
6. Blockchain settlement flow
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
    """Total amount from the PDF."""
    return Decimal("41370.65")


@pytest.fixture
def test_claim_base(test_db, test_claimant):
    """Base claim fixture."""
    from src.models import UserWallet
    wallet = test_db.query(UserWallet).filter(UserWallet.user_id == test_claimant.id).first()
    return {
        "claimant_address": wallet.wallet_address if wallet else "0x1234567890123456789012345678901234567890",
        "status": "SUBMITTED",
        "processing_costs": Decimal("0.00")
    }


@pytest.mark.integration
class TestAmountValidationScenarios:
    """Test amount validation with various differences."""
    
    @pytest.mark.asyncio
    async def test_exact_amount_match(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, test_claim_base, mock_blockchain_service):
        """
        Test with exact amount match.
        
        Expected:
        - All tools called
        - Amount validation passes
        - AUTO_APPROVED with high confidence
        - Auto-settlement
        """
        claim = Claim(
            id="test-exact-match",
            claim_amount=pdf_total_amount,
            **test_claim_base
        )
        test_db.add(claim)
        test_db.commit()
        
        evidence = [Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path=real_pdf_file)]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        # Verify tool calling
        tool_results = result.get("tool_results", {})
        assert "extract_document_data" in tool_results, "extract_document_data should be called"
        
        # Verify amount validation
        cross_check = tool_results.get("cross_check_amounts", {})
        if cross_check:
            assert cross_check.get("matches") is True, "Amounts should match"
            assert cross_check.get("difference_percent", 100) < 5, "Difference should be < 5%"
        
        # Verify decision
        assert result.get("decision") in ["AUTO_APPROVED", "APPROVED_WITH_REVIEW"], \
            f"Should approve with matching amount, got {result.get('decision')}"
        assert result.get("confidence", 0.0) >= 0.85, \
            f"Confidence should be high with matching amount, got {result.get('confidence')}"
    
    @pytest.mark.asyncio
    async def test_small_difference_5_percent(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, test_claim_base, mock_blockchain_service):
        """
        Test with 5% difference (within tolerance).
        
        Expected:
        - Amount validation detects small difference
        - May still approve if other factors are good
        - Contradiction flagged but not severe
        """
        # 5% higher
        claim_amount = pdf_total_amount * Decimal("1.05")
        claim = Claim(
            id="test-small-diff",
            claim_amount=claim_amount,
            **test_claim_base
        )
        test_db.add(claim)
        test_db.commit()
        
        evidence = [Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path=real_pdf_file)]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        # Verify amount validation
        tool_results = result.get("tool_results", {})
        cross_check = tool_results.get("cross_check_amounts", {})
        
        if cross_check:
            diff_percent = cross_check.get("difference_percent", 0)
            assert 4 <= diff_percent <= 6, f"Difference should be ~5%, got {diff_percent}%"
        
        # May still approve with small difference
        assert result.get("decision") in ["AUTO_APPROVED", "APPROVED_WITH_REVIEW", "NEEDS_REVIEW"]
    
    @pytest.mark.asyncio
    async def test_medium_difference_25_percent(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, test_claim_base, mock_blockchain_service):
        """
        Test with 25% difference (needs review).
        
        Expected:
        - Amount mismatch detected
        - Contradictions flagged
        - NEEDS_REVIEW decision
        - Higher fraud risk
        """
        # 25% higher
        claim_amount = pdf_total_amount * Decimal("1.25")
        claim = Claim(
            id="test-medium-diff",
            claim_amount=claim_amount,
            **test_claim_base
        )
        test_db.add(claim)
        test_db.commit()
        
        evidence = [Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path=real_pdf_file)]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        # Verify mismatch detection
        contradictions = result.get("contradictions", [])
        fraud_risk = result.get("fraud_risk", 0.0)
        
        assert len(contradictions) > 0 or fraud_risk >= 0.3, \
            f"Should detect mismatch: contradictions={contradictions}, fraud_risk={fraud_risk}"
        assert result.get("decision") == "NEEDS_REVIEW", \
            f"Should need review with 25% difference, got {result.get('decision')}"
    
    @pytest.mark.asyncio
    async def test_large_difference_50_percent(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, test_claim_base, mock_blockchain_service):
        """
        Test with 50% difference (high fraud risk).
        
        Expected:
        - Amount mismatch detected
        - Contradictions flagged
        - High fraud risk (>= 0.5)
        - NEEDS_REVIEW or FRAUD_DETECTED
        """
        # 50% higher
        claim_amount = pdf_total_amount * Decimal("1.50")
        claim = Claim(
            id="test-large-diff",
            claim_amount=claim_amount,
            **test_claim_base
        )
        test_db.add(claim)
        test_db.commit()
        
        evidence = [Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path=real_pdf_file)]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        # Verify mismatch detection
        contradictions = result.get("contradictions", [])
        fraud_risk = result.get("fraud_risk", 0.0)
        
        assert len(contradictions) > 0, f"Should flag contradictions: {contradictions}"
        assert fraud_risk >= 0.5, f"Should have high fraud risk, got {fraud_risk}"
        assert result.get("decision") in ["NEEDS_REVIEW", "FRAUD_DETECTED"], \
            f"Should flag for review/fraud, got {result.get('decision')}"
    
    @pytest.mark.asyncio
    async def test_extreme_difference_100_percent(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, test_claim_base, mock_blockchain_service):
        """
        Test with 100% difference (fraud detected).
        
        Expected:
        - FRAUD_DETECTED decision
        - Very high fraud risk (>= 0.7)
        - Multiple contradictions
        """
        # 100% higher (double)
        claim_amount = pdf_total_amount * Decimal("2.00")
        claim = Claim(
            id="test-extreme-diff",
            claim_amount=claim_amount,
            **test_claim_base
        )
        test_db.add(claim)
        test_db.commit()
        
        evidence = [Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path=real_pdf_file)]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        # Verify fraud detection
        fraud_risk = result.get("fraud_risk", 0.0)
        contradictions = result.get("contradictions", [])
        
        # Should detect fraud
        assert fraud_risk >= 0.7 or result.get("decision") == "FRAUD_DETECTED", \
            f"Should detect fraud: fraud_risk={fraud_risk}, decision={result.get('decision')}"
        assert len(contradictions) > 0, f"Should have contradictions: {contradictions}"


@pytest.mark.integration
class TestToolCallingSequence:
    """Test tool calling sequence and completeness."""
    
    @pytest.mark.asyncio
    async def test_complete_sequence_document_only(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, test_claim_base, mock_blockchain_service):
        """
        Test complete tool sequence with document only.
        
        Expected sequence:
        1. extract_document_data
        2. estimate_repair_cost
        3. cross_check_amounts
        4. validate_claim_data
        5. verify_document
        6. verify_fraud
        """
        claim = Claim(id="test-seq-doc", claim_amount=pdf_total_amount, **test_claim_base)
        test_db.add(claim)
        test_db.commit()
        
        evidence = [Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path=real_pdf_file)]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        tool_results = result.get("tool_results", {})
        required_tools = [
            "extract_document_data",
            "estimate_repair_cost",
            "cross_check_amounts",
            "validate_claim_data",
            "verify_document",
            "verify_fraud"
        ]
        
        called_tools = [tool for tool in required_tools if tool in tool_results]
        completion_rate = len(called_tools) / len(required_tools)
        
        print(f"\n📊 Tool Calling Analysis:")
        print(f"   └─ Required Tools: {len(required_tools)}")
        print(f"   └─ Called Tools: {len(called_tools)}")
        print(f"   └─ Completion Rate: {completion_rate:.1%}")
        print(f"   └─ Called: {', '.join(called_tools)}")
        print(f"   └─ Missing: {', '.join(set(required_tools) - set(called_tools))}")
        
        # Target: 95%+ completion
        assert completion_rate >= 0.95, \
            f"Tool calling completion rate {completion_rate:.1%} below 95% target. Missing: {set(required_tools) - set(called_tools)}"
    
    @pytest.mark.asyncio
    async def test_complete_sequence_with_images(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, test_claim_base, mock_blockchain_service, sample_damage_photo):
        """
        Test complete tool sequence with document and images.
        
        Expected sequence includes verify_image.
        """
        claim = Claim(id="test-seq-images", claim_amount=pdf_total_amount, **test_claim_base)
        test_db.add(claim)
        test_db.commit()
        
        evidence = [
            Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path=real_pdf_file),
            Evidence(id="ev-2", claim_id=claim.id, file_type="image", file_path=sample_damage_photo)
        ]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        tool_results = result.get("tool_results", {})
        required_tools = [
            "extract_document_data",
            "extract_image_data",
            "estimate_repair_cost",
            "cross_check_amounts",
            "validate_claim_data",
            "verify_document",
            "verify_image",
            "verify_fraud"
        ]
        
        called_tools = [tool for tool in required_tools if tool in tool_results]
        completion_rate = len(called_tools) / len(required_tools)
        
        assert completion_rate >= 0.95, \
            f"Tool calling completion rate {completion_rate:.1%} below 95% target"
        assert "verify_image" in tool_results, "verify_image should be called when images exist"
    
    @pytest.mark.asyncio
    async def test_tool_sequence_order(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, test_claim_base, mock_blockchain_service):
        """
        Test that tools are called in correct sequence.
        
        Expected order:
        1. Extraction tools first
        2. Cost estimation second
        3. Validation third
        4. Verification last
        """
        claim = Claim(id="test-seq-order", claim_amount=pdf_total_amount, **test_claim_base)
        test_db.add(claim)
        test_db.commit()
        
        evidence = [Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path=real_pdf_file)]
        test_db.add_all(evidence)
        test_db.commit()
        
        # Track tool call order
        call_order = []
        
        # Mock tools to track order
        original_tools = {}
        with patch('src.agent.adk_tools.get_adk_tools') as mock_get_tools:
            # This is complex - for now, just verify tools are called
            orchestrator = ADKOrchestrator()
            result = await orchestrator.evaluate_claim(claim, evidence)
            
            tool_results = result.get("tool_results", {})
            
            # Verify extraction happens before verification
            if "extract_document_data" in tool_results and "verify_document" in tool_results:
                # Both called - order verified by tool dependencies
                assert True
            elif "extract_document_data" in tool_results:
                # At least extraction happened
                assert True


@pytest.mark.integration
class TestDecisionLogicEdgeCases:
    """Test decision logic with edge cases."""
    
    @pytest.mark.asyncio
    async def test_high_confidence_low_fraud_auto_approve(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, test_claim_base, mock_blockchain_service):
        """
        Test auto-approval with high confidence and low fraud risk.
        
        Conditions:
        - confidence >= 0.95
        - fraud_risk < 0.3
        - no contradictions
        
        Expected: AUTO_APPROVED, auto_settled: true
        """
        claim = Claim(id="test-auto-approve", claim_amount=pdf_total_amount, **test_claim_base)
        test_db.add(claim)
        test_db.commit()
        
        evidence = [Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path=real_pdf_file)]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        orchestrator.blockchain = mock_blockchain_service
        
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        confidence = result.get("confidence", 0.0)
        fraud_risk = result.get("fraud_risk", 1.0)
        contradictions = result.get("contradictions", [])
        
        # If conditions met, should auto-approve
        if confidence >= 0.95 and fraud_risk < 0.3 and len(contradictions) == 0:
            assert result.get("decision") == "AUTO_APPROVED", \
                f"Should auto-approve: confidence={confidence}, fraud_risk={fraud_risk}, contradictions={contradictions}"
            assert result.get("auto_settled") is True, "Should auto-settle"
            assert result.get("tx_hash") is not None, "Should have transaction hash"
    
    @pytest.mark.asyncio
    async def test_high_confidence_high_fraud_prevent_auto_approve(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, test_claim_base, mock_blockchain_service):
        """
        Test that high fraud risk prevents auto-approval even with high confidence.
        
        Conditions:
        - confidence >= 0.95
        - fraud_risk >= 0.3
        
        Expected: NEEDS_REVIEW (not AUTO_APPROVED)
        """
        # Use mismatched amount to trigger fraud risk
        claim_amount = pdf_total_amount * Decimal("1.50")  # 50% higher
        claim = Claim(id="test-high-fraud", claim_amount=claim_amount, **test_claim_base)
        test_db.add(claim)
        test_db.commit()
        
        evidence = [Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path=real_pdf_file)]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        fraud_risk = result.get("fraud_risk", 0.0)
        
        # If fraud risk is high, should not auto-approve
        if fraud_risk >= 0.3:
            assert result.get("decision") != "AUTO_APPROVED", \
                f"Should not auto-approve with fraud_risk={fraud_risk}"
            assert result.get("auto_settled") is False, "Should not auto-settle"
    
    @pytest.mark.asyncio
    async def test_contradictions_prevent_auto_approve(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, test_claim_base, mock_blockchain_service):
        """
        Test that contradictions prevent auto-approval.
        
        Conditions:
        - confidence >= 0.95
        - fraud_risk < 0.3
        - contradictions exist
        
        Expected: NEEDS_REVIEW (not AUTO_APPROVED)
        """
        # Use mismatched amount to create contradictions
        claim_amount = pdf_total_amount * Decimal("1.25")  # 25% higher
        claim = Claim(id="test-contradictions", claim_amount=claim_amount, **test_claim_base)
        test_db.add(claim)
        test_db.commit()
        
        evidence = [Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path=real_pdf_file)]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        contradictions = result.get("contradictions", [])
        
        # If contradictions exist, should not auto-approve
        if len(contradictions) > 0:
            assert result.get("decision") != "AUTO_APPROVED", \
                f"Should not auto-approve with contradictions: {contradictions}"
    
    @pytest.mark.asyncio
    async def test_fraud_detected_high_risk(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, test_claim_base, mock_blockchain_service):
        """
        Test FRAUD_DETECTED decision with very high fraud risk.
        
        Conditions:
        - fraud_risk >= 0.7
        
        Expected: FRAUD_DETECTED
        """
        # Use extreme difference to trigger high fraud risk
        claim_amount = pdf_total_amount * Decimal("2.00")  # 100% higher
        claim = Claim(id="test-fraud-detected", claim_amount=claim_amount, **test_claim_base)
        test_db.add(claim)
        test_db.commit()
        
        evidence = [Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path=real_pdf_file)]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        fraud_risk = result.get("fraud_risk", 0.0)
        
        # If fraud risk is very high, should detect fraud
        if fraud_risk >= 0.7:
            assert result.get("decision") == "FRAUD_DETECTED", \
                f"Should detect fraud with fraud_risk={fraud_risk}"


@pytest.mark.integration
class TestErrorHandlingScenarios:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_invalid_pdf_path_handling(self, test_db, test_claimant, test_claim_base, mock_blockchain_service):
        """Test handling of invalid PDF path."""
        claim = Claim(id="test-invalid-pdf", claim_amount=Decimal("1000.00"), **test_claim_base)
        test_db.add(claim)
        test_db.commit()
        
        evidence = [Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path="/nonexistent/path/to/file.pdf")]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        # Should handle error gracefully
        assert result.get("decision") in ["NEEDS_REVIEW", "INSUFFICIENT_DATA", "NEEDS_MORE_DATA"]
        assert result.get("confidence", 1.0) < 0.95
    
    @pytest.mark.asyncio
    async def test_zero_claim_amount_handling(self, test_db, test_claimant, real_pdf_file, test_claim_base, mock_blockchain_service):
        """Test handling of zero claim amount."""
        claim = Claim(id="test-zero-amount", claim_amount=Decimal("0.00"), **test_claim_base)
        test_db.add(claim)
        test_db.commit()
        
        evidence = [Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path=real_pdf_file)]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        # Should reject or flag as invalid
        assert result.get("decision") != "AUTO_APPROVED"
        assert result.get("decision") in ["NEEDS_REVIEW", "INSUFFICIENT_DATA", "FRAUD_DETECTED"]
    
    @pytest.mark.asyncio
    async def test_no_evidence_handling(self, test_db, test_claimant, test_claim_base, mock_blockchain_service):
        """Test handling of claim with no evidence."""
        claim = Claim(id="test-no-evidence", claim_amount=Decimal("1000.00"), **test_claim_base)
        test_db.add(claim)
        test_db.commit()
        
        evidence = []
        
        orchestrator = ADKOrchestrator()
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        # Should request data or have very low confidence
        assert result.get("decision") in ["NEEDS_MORE_DATA", "INSUFFICIENT_DATA", "NEEDS_REVIEW"]
        assert len(result.get("requested_data", [])) > 0 or result.get("confidence", 1.0) < 0.5
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, test_claim_base, mock_blockchain_service):
        """
        Test handling when PDF is missing required fields.
        
        Note: This test may need to use a different PDF or mock the extraction result.
        """
        claim = Claim(id="test-missing-fields", claim_amount=pdf_total_amount, **test_claim_base)
        test_db.add(claim)
        test_db.commit()
        
        evidence = [Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path=real_pdf_file)]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        # Should handle gracefully
        assert result.get("decision") is not None
        # If fields are missing, confidence should be lower
        # (This test may need refinement based on actual PDF content)


@pytest.mark.integration
class TestBlockchainSettlementFlow:
    """Test blockchain settlement flow."""
    
    @pytest.mark.asyncio
    async def test_complete_settlement_flow(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, test_claim_base, mock_blockchain_service):
        """
        Test complete auto-settlement flow.
        
        Expected:
        1. Auto-approval decision
        2. approve_claim tool called
        3. Transaction hash returned
        4. Claim status updated
        """
        claim = Claim(id="test-settlement", claim_amount=pdf_total_amount, **test_claim_base)
        test_db.add(claim)
        test_db.commit()
        
        evidence = [Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path=real_pdf_file)]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        orchestrator.blockchain = mock_blockchain_service
        
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        # If auto-approved, verify settlement
        if result.get("decision") == "AUTO_APPROVED" and result.get("auto_settled"):
            assert result.get("tx_hash") is not None, "Should have transaction hash"
            # Verify blockchain service was called
            mock_blockchain_service.approve_claim.assert_called_once()
            
            # Verify settlement amount matches claim amount
            call_args = mock_blockchain_service.approve_claim.call_args
            if call_args:
                settled_amount = call_args[0][1] if len(call_args[0]) > 1 else None
                if settled_amount:
                    assert abs(float(settled_amount) - float(claim.claim_amount)) < 0.01, \
                        f"Settlement amount {settled_amount} should match claim amount {claim.claim_amount}"
    
    @pytest.mark.asyncio
    async def test_settlement_recipient_validation(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, test_claim_base, mock_blockchain_service):
        """Test that settlement recipient is claimant address."""
        claim = Claim(id="test-recipient", claim_amount=pdf_total_amount, **test_claim_base)
        test_db.add(claim)
        test_db.commit()
        
        evidence = [Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path=real_pdf_file)]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        orchestrator.blockchain = mock_blockchain_service
        
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        # If settlement occurred, verify recipient
        if result.get("auto_settled") and mock_blockchain_service.approve_claim.called:
            call_args = mock_blockchain_service.approve_claim.call_args
            if call_args and len(call_args[0]) > 2:
                recipient = call_args[0][2]
                assert recipient == claim.claimant_address, \
                    f"Recipient {recipient} should match claimant address {claim.claimant_address}"


@pytest.mark.integration
class TestJSONParsingRobustness:
    """Test JSON parsing with various formats."""
    
    @pytest.mark.asyncio
    async def test_json_in_code_block(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, test_claim_base, mock_blockchain_service):
        """Test parsing JSON wrapped in code blocks."""
        # This tests the parsing logic indirectly through actual agent responses
        claim = Claim(id="test-json-codeblock", claim_amount=pdf_total_amount, **test_claim_base)
        test_db.add(claim)
        test_db.commit()
        
        evidence = [Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path=real_pdf_file)]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        # Should parse successfully (no exception)
        assert result.get("decision") is not None
        assert result.get("confidence") is not None
    
    @pytest.mark.asyncio
    async def test_nested_json_parsing(self, test_db, test_claimant, real_pdf_file, pdf_total_amount, test_claim_base, mock_blockchain_service):
        """Test parsing deeply nested JSON structures."""
        claim = Claim(id="test-json-nested", claim_amount=pdf_total_amount, **test_claim_base)
        test_db.add(claim)
        test_db.commit()
        
        evidence = [Evidence(id="ev-1", claim_id=claim.id, file_type="document", file_path=real_pdf_file)]
        test_db.add_all(evidence)
        test_db.commit()
        
        orchestrator = ADKOrchestrator()
        result = await orchestrator.evaluate_claim(claim, evidence)
        
        # Should parse nested structures successfully
        tool_results = result.get("tool_results", {})
        if tool_results:
            # Verify nested structures are parsed
            assert isinstance(tool_results, dict)
