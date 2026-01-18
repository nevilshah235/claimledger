"""
End-to-end tests for complete claim evaluation flow.
"""

import pytest
from unittest.mock import AsyncMock, patch
from decimal import Decimal
from io import BytesIO


@pytest.mark.integration
class TestE2EAgentFlow:
    """End-to-end test suite for claim evaluation flow."""
    
    def test_full_claim_evaluation_flow(self, client, test_db, test_claimant, auth_headers, sample_pdf_file, sample_damage_photo, mock_blockchain_service):
        """Complete flow from claim creation to settlement."""
        from src.models import Claim, Evidence
        
        # Step 1: Create claim
        with open(sample_pdf_file, "rb") as pdf_f, open(sample_damage_photo, "rb") as img_f:
            files = [
                ("files", ("invoice.pdf", BytesIO(pdf_f.read()), "application/pdf")),
                ("files", ("damage.jpg", BytesIO(img_f.read()), "image/jpeg"))
            ]
        
        create_response = client.post(
            "/claims",
            headers=auth_headers,
            data={"claim_amount": "3500.00"},
            files=files
        )
        
        assert create_response.status_code == 200
        claim_id = create_response.json()["claim_id"]
        
        # Step 2: Verify claim was created
        claim = test_db.query(Claim).filter(Claim.id == claim_id).first()
        assert claim is not None
        assert claim.status == "SUBMITTED"
        
        # Step 3: Evaluate claim
        eval_response = client.post(f"/agent/evaluate/{claim_id}")
        
        assert eval_response.status_code == 200
        eval_data = eval_response.json()
        
        assert "decision" in eval_data
        assert "confidence" in eval_data
        assert "reasoning" in eval_data
        
        # Step 4: Verify claim status updated
        test_db.refresh(claim)
        assert claim.status in ["APPROVED", "NEEDS_REVIEW", "SETTLED"]
        assert claim.decision is not None
        assert claim.confidence is not None
        
        # Step 5: Verify evidence was processed
        evidence = test_db.query(Evidence).filter(Evidence.claim_id == claim_id).all()
        assert len(evidence) > 0
    
    def test_auto_approval_flow(self, client, test_db, test_claimant, auth_headers, sample_pdf_file, sample_damage_photo, mock_blockchain_service):
        """Full auto-approval and settlement flow."""
        from src.models import Claim, Evidence, AgentResult
        
        # Create claim with evidence
        with open(sample_pdf_file, "rb") as pdf_f, open(sample_damage_photo, "rb") as img_f:
            files = [
                ("files", ("invoice.pdf", BytesIO(pdf_f.read()), "application/pdf")),
                ("files", ("damage.jpg", BytesIO(img_f.read()), "image/jpeg"))
            ]
        
        create_response = client.post(
            "/claims",
            headers=auth_headers,
            data={"claim_amount": "2000.00"},
            files=files
        )
        
        claim_id = create_response.json()["claim_id"]
        
        # Mock orchestrator to return high confidence
        with patch("src.api.agent.get_adk_orchestrator") as mock_get:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.evaluate_claim = AsyncMock(return_value={
                "decision": "AUTO_APPROVED",
                "confidence": 0.96,
                "summary": "High confidence auto-approval",
                "agent_results": {
                    "document": {"valid": True, "confidence": 0.95},
                    "image": {"valid": True, "confidence": 0.95},
                    "fraud": {"fraud_score": 0.05, "risk_level": "LOW"}
                },
                "reasoning": {
                    "final_confidence": 0.96,
                    "contradictions": [],
                    "fraud_risk": 0.05
                },
                "auto_settled": True,
                "tx_hash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                "review_reasons": None
            })
            mock_get.return_value = mock_orchestrator
            
            # Evaluate claim
            eval_response = client.post(f"/agent/evaluate/{claim_id}")
            
            assert eval_response.status_code == 200
            eval_data = eval_response.json()
            
            assert eval_data["decision"] == "AUTO_APPROVED"
            assert eval_data["auto_approved"] is True
            assert eval_data["auto_settled"] is True
            assert eval_data["tx_hash"] is not None
            
            # Verify claim status
            claim = test_db.query(Claim).filter(Claim.id == claim_id).first()
            test_db.refresh(claim)
            assert claim.status == "SETTLED"
            assert claim.auto_approved is True
            assert claim.auto_settled is True
            assert claim.tx_hash is not None
    
    def test_manual_review_flow(self, client, test_db, test_claimant, auth_headers, sample_pdf_file, sample_damage_photo, mock_blockchain_service):
        """Flow for claims requiring manual review."""
        from src.models import Claim
        
        # Create claim
        with open(sample_pdf_file, "rb") as pdf_f:
            files = [
                ("files", ("invoice.pdf", BytesIO(pdf_f.read()), "application/pdf"))
            ]
        
        create_response = client.post(
            "/claims",
            headers=auth_headers,
            data={"claim_amount": "5000.00"},
            files=files
        )
        
        claim_id = create_response.json()["claim_id"]
        
        # Mock orchestrator to return low confidence
        with patch("src.api.agent.get_adk_orchestrator") as mock_get:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.evaluate_claim = AsyncMock(return_value={
                "decision": "NEEDS_REVIEW",
                "confidence": 0.75,
                "summary": "Requires manual review",
                "agent_results": {
                    "document": {"valid": True, "confidence": 0.7},
                    "fraud": {"fraud_score": 0.4, "risk_level": "MEDIUM"}
                },
                "reasoning": {
                    "final_confidence": 0.75,
                    "contradictions": [],
                    "fraud_risk": 0.4
                },
                "auto_settled": False,
                "tx_hash": None,
                "review_reasons": ["Confidence 75.00% below 95% threshold", "High fraud risk: 0.40"]
            })
            mock_get.return_value = mock_orchestrator
            
            # Evaluate claim
            eval_response = client.post(f"/agent/evaluate/{claim_id}")
            
            assert eval_response.status_code == 200
            eval_data = eval_response.json()
            
            assert eval_data["decision"] == "NEEDS_REVIEW"
            assert eval_data["auto_approved"] is False
            assert eval_data["auto_settled"] is False
            assert eval_data["review_reasons"] is not None
            assert len(eval_data["review_reasons"]) > 0
            
            # Verify claim status
            claim = test_db.query(Claim).filter(Claim.id == claim_id).first()
            test_db.refresh(claim)
            assert claim.status == "NEEDS_REVIEW"
            assert claim.auto_approved is False
            assert claim.review_reasons is not None
    
    def test_claim_with_real_files(self, client, test_db, test_claimant, auth_headers, sample_pdf_file, sample_damage_photo, mock_blockchain_service):
        """Test with actual PDF and image files."""
        from src.models import Claim, Evidence
        
        # Create claim with real files
        with open(sample_pdf_file, "rb") as pdf_f, open(sample_damage_photo, "rb") as img_f:
            files = [
                ("files", ("invoice.pdf", BytesIO(pdf_f.read()), "application/pdf")),
                ("files", ("damage.jpg", BytesIO(img_f.read()), "image/jpeg"))
            ]
        
        create_response = client.post(
            "/claims",
            headers=auth_headers,
            data={"claim_amount": "3000.00"},
            files=files
        )
        
        assert create_response.status_code == 200
        claim_id = create_response.json()["claim_id"]
        
        # Verify files were stored
        evidence = test_db.query(Evidence).filter(Evidence.claim_id == claim_id).all()
        assert len(evidence) == 2
        
        # Evaluate claim
        eval_response = client.post(f"/agent/evaluate/{claim_id}")
        
        assert eval_response.status_code == 200
        eval_data = eval_response.json()
        
        assert "decision" in eval_data
        assert "confidence" in eval_data
    
    def test_multiple_claims_sequential(self, client, test_db, test_claimant, auth_headers, sample_pdf_file, mock_blockchain_service):
        """Test processing multiple claims sequentially."""
        from src.models import Claim
        
        claim_ids = []
        
        # Create 3 claims
        for i in range(3):
            with open(sample_pdf_file, "rb") as pdf_f:
                files = [
                    ("files", ("invoice.pdf", BytesIO(pdf_f.read()), "application/pdf"))
                ]
            
            create_response = client.post(
                "/claims",
                headers=auth_headers,
                data={"claim_amount": f"{1000 + i * 500}.00"},
                files=files
            )
            
            assert create_response.status_code == 200
            claim_ids.append(create_response.json()["claim_id"])
        
        # Evaluate all claims sequentially
        for claim_id in claim_ids:
            eval_response = client.post(f"/agent/evaluate/{claim_id}")
            assert eval_response.status_code == 200
            
            # Verify each claim was processed
            claim = test_db.query(Claim).filter(Claim.id == claim_id).first()
            test_db.refresh(claim)
            assert claim.status in ["APPROVED", "NEEDS_REVIEW", "SETTLED"]
    
    def test_claim_re_evaluation(self, client, test_db, test_claim, mock_blockchain_service):
        """Test re-evaluating a claim."""
        from src.models import Claim
        
        # First evaluation
        response1 = client.post(f"/agent/evaluate/{test_claim.id}")
        assert response1.status_code == 200
        
        test_db.refresh(test_claim)
        first_decision = test_claim.decision
        first_confidence = test_claim.confidence
        
        # Reset claim status for re-evaluation
        test_claim.status = "SUBMITTED"
        test_claim.decision = None
        test_claim.confidence = None
        test_db.commit()
        
        # Re-evaluate
        response2 = client.post(f"/agent/evaluate/{test_claim.id}")
        assert response2.status_code == 200
        
        test_db.refresh(test_claim)
        
        # Should have new evaluation
        assert test_claim.decision is not None
        assert test_claim.confidence is not None
    
    def test_agent_results_endpoint(self, client, test_db, test_claim, mock_blockchain_service):
        """Test GET /agent/results/{claim_id} endpoint."""
        from src.models import AgentResult
        
        # First evaluate the claim
        eval_response = client.post(f"/agent/evaluate/{test_claim.id}")
        assert eval_response.status_code == 200
        
        # Get agent results
        results_response = client.get(f"/agent/results/{test_claim.id}")
        assert results_response.status_code == 200
        
        results_data = results_response.json()
        assert "claim_id" in results_data
        assert "agent_results" in results_data
        assert results_data["claim_id"] == test_claim.id
        assert isinstance(results_data["agent_results"], list)
        
        # Verify agent results were stored
        stored_results = test_db.query(AgentResult).filter(AgentResult.claim_id == test_claim.id).all()
        assert len(stored_results) > 0
    
    def test_evaluation_status_endpoint(self, client, test_db, test_claim, mock_blockchain_service):
        """Test GET /agent/status/{claim_id} endpoint."""
        from src.models import AgentResult
        
        # Get status before evaluation
        status_response = client.get(f"/agent/status/{test_claim.id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert "claim_id" in status_data
        assert "status" in status_data
        assert "completed_agents" in status_data
        assert "pending_agents" in status_data
        assert "progress_percentage" in status_data
        assert status_data["claim_id"] == test_claim.id
        
        # Evaluate claim
        eval_response = client.post(f"/agent/evaluate/{test_claim.id}")
        assert eval_response.status_code == 200
        
        # Get status after evaluation
        status_response = client.get(f"/agent/status/{test_claim.id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert len(status_data["completed_agents"]) > 0
        assert status_data["progress_percentage"] > 0
    
    def test_evaluation_response_includes_agent_results(self, client, test_db, test_claimant, auth_headers, sample_pdf_file, mock_blockchain_service):
        """Test that evaluation response includes agent_results and tool_calls."""
        from src.models import Claim
        
        # Create claim
        with open(sample_pdf_file, "rb") as pdf_f:
            files = [
                ("files", ("invoice.pdf", BytesIO(pdf_f.read()), "application/pdf"))
            ]
        
        create_response = client.post(
            "/claims",
            headers=auth_headers,
            data={"claim_amount": "1500.00"},
            files=files
        )
        
        claim_id = create_response.json()["claim_id"]
        
        # Evaluate claim
        eval_response = client.post(f"/agent/evaluate/{claim_id}")
        assert eval_response.status_code == 200
        
        eval_data = eval_response.json()
        
        # Check for new fields
        assert "agent_results" in eval_data or eval_data.get("agent_results") is not None
        # tool_calls may be None if not available
        assert "tool_calls" in eval_data
    
    def test_all_decision_types(self, client, test_db, test_claimant, auth_headers, sample_pdf_file, mock_blockchain_service):
        """Test all decision types are properly handled."""
        from src.models import Claim
        
        decision_types = [
            "AUTO_APPROVED",
            "APPROVED_WITH_REVIEW",
            "NEEDS_REVIEW",
            "NEEDS_MORE_DATA",
            "INSUFFICIENT_DATA"
        ]
        
        for decision_type in decision_types:
            # Create claim
            with open(sample_pdf_file, "rb") as pdf_f:
                files = [
                    ("files", ("invoice.pdf", BytesIO(pdf_f.read()), "application/pdf"))
                ]
            
            create_response = client.post(
                "/claims",
                headers=auth_headers,
                data={"claim_amount": "1000.00"},
                files=files
            )
            
            claim_id = create_response.json()["claim_id"]
            
            # Mock orchestrator to return specific decision
            with patch("src.api.agent.get_adk_orchestrator") as mock_get:
                mock_orchestrator = AsyncMock()
                mock_orchestrator.evaluate_claim = AsyncMock(return_value={
                    "decision": decision_type,
                    "confidence": 0.8 if decision_type != "INSUFFICIENT_DATA" else 0.3,
                    "summary": f"Test {decision_type}",
                    "agent_results": {
                        "document": {"valid": True, "confidence": 0.8}
                    },
                    "reasoning": {
                        "final_confidence": 0.8 if decision_type != "INSUFFICIENT_DATA" else 0.3,
                        "contradictions": [],
                        "fraud_risk": 0.2
                    },
                    "auto_settled": False,
                    "tx_hash": None,
                    "review_reasons": None if decision_type == "AUTO_APPROVED" else ["Test reason"],
                    "requested_data": ["document", "image"] if decision_type in ["NEEDS_MORE_DATA", "INSUFFICIENT_DATA"] else None,
                    "human_review_required": decision_type in ["APPROVED_WITH_REVIEW", "NEEDS_REVIEW"]
                })
                mock_get.return_value = mock_orchestrator
                
                # Evaluate claim
                eval_response = client.post(f"/agent/evaluate/{claim_id}")
                assert eval_response.status_code == 200
                
                eval_data = eval_response.json()
                assert eval_data["decision"] == decision_type
                
                # Verify claim status is correct
                claim = test_db.query(Claim).filter(Claim.id == claim_id).first()
                test_db.refresh(claim)
                
                if decision_type == "AUTO_APPROVED":
                    assert claim.status in ["APPROVED", "SETTLED"]
                elif decision_type in ["NEEDS_MORE_DATA", "INSUFFICIENT_DATA"]:
                    assert claim.status == "AWAITING_DATA"
                elif decision_type == "APPROVED_WITH_REVIEW":
                    assert claim.status == "APPROVED"
                else:
                    assert claim.status == "NEEDS_REVIEW"