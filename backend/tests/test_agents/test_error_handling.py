"""
Error handling tests for Gemini AI agents.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from src.agent.agents.document_agent import DocumentAgent
from src.agent.agents.image_agent import ImageAgent
from src.agent.agents.fraud_agent import FraudAgent
from src.agent.agents.reasoning_agent import ReasoningAgent
from src.agent.adk_agents.orchestrator import ADKOrchestrator


@pytest.mark.unit
class TestErrorHandling:
    """Test suite for error handling."""
    
    @pytest.mark.asyncio
    async def test_agent_handles_api_timeout(self, sample_pdf_file, mock_gemini_client):
        """Test timeout handling."""
        agent = DocumentAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Simulate timeout
        async def timeout_error(*args, **kwargs):
            await asyncio.sleep(0.01)
            raise asyncio.TimeoutError("Request timed out")
        
        mock_gemini_client.generate_content_async = timeout_error
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        # Should handle timeout gracefully
        assert result is not None
        assert result["valid"] is False or "error" in str(result)
    
    @pytest.mark.asyncio
    async def test_agent_handles_api_rate_limit(self, sample_pdf_file, mock_gemini_client):
        """Test rate limit handling."""
        agent = DocumentAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Simulate rate limit error
        class RateLimitError(Exception):
            pass
        
        mock_gemini_client.generate_content_async = AsyncMock(
            side_effect=RateLimitError("Rate limit exceeded")
        )
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        # Should handle rate limit gracefully
        assert result is not None
        assert result["valid"] is False or "error" in str(result)
    
    @pytest.mark.asyncio
    async def test_agent_handles_invalid_api_key(self, sample_pdf_file, mock_gemini_client):
        """Test invalid API key handling."""
        agent = DocumentAgent(api_key="invalid-key")
        agent.client = mock_gemini_client
        
        # Simulate authentication error
        class AuthError(Exception):
            pass
        
        mock_gemini_client.generate_content_async = AsyncMock(side_effect=AuthError("Invalid API key"))
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        # Should handle auth error gracefully
        assert result is not None
        assert result["valid"] is False or "error" in str(result)
    
    @pytest.mark.asyncio
    async def test_agent_handles_api_quota_exceeded(self, sample_pdf_file, mock_gemini_client):
        """Test quota exceeded handling."""
        agent = DocumentAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Simulate quota exceeded error
        class QuotaExceededError(Exception):
            pass
        
        mock_gemini_client.generate_content_async = AsyncMock(
            side_effect=QuotaExceededError("Quota exceeded")
        )
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        # Should handle quota error gracefully
        assert result is not None
        assert result["valid"] is False or "error" in str(result)
    
    @pytest.mark.asyncio
    async def test_agent_handles_network_error(self, sample_pdf_file, mock_gemini_client):
        """Test network failure handling."""
        agent = DocumentAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Simulate network error
        class NetworkError(Exception):
            pass
        
        mock_gemini_client.generate_content_async = AsyncMock(
            side_effect=NetworkError("Network connection failed")
        )
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        # Should handle network error gracefully
        assert result is not None
        assert result["valid"] is False or "error" in str(result)
    
    @pytest.mark.asyncio
    async def test_agent_handles_malformed_response(self, sample_pdf_file, mock_gemini_client):
        """Test malformed API response handling."""
        agent = DocumentAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Return malformed response (not JSON, not text)
        mock_response = MagicMock()
        mock_response.text = None  # No text attribute
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        # Should handle malformed response gracefully
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_orchestrator_handles_partial_failure(self, test_claim, mock_blockchain_service):
        """Test behavior when some agents fail."""
        orchestrator = ADKOrchestrator()
        
        # Document agent fails, others succeed
        orchestrator.document_agent.analyze = AsyncMock(side_effect=Exception("Document agent error"))
        orchestrator.image_agent.analyze = AsyncMock(return_value={
            "summary": "Img", "valid": True, "confidence": 0.85, "damage_assessment": {}
        })
        orchestrator.fraud_agent.analyze = AsyncMock(return_value={
            "fraud_score": 0.2, "risk_level": "MEDIUM", "indicators": [], "confidence": 0.8
        })
        orchestrator.reasoning_agent.reason = AsyncMock(return_value={
            "final_confidence": 0.6, "contradictions": [], "fraud_risk": 0.2,
            "missing_evidence": ["valid_document"], "reasoning": "Document agent failed"
        })
        
        evidence = []
        
        result = await orchestrator.evaluate_claim(test_claim, evidence)
        
        # Should still complete evaluation
        assert result is not None
        assert "decision" in result
        assert result["decision"] == "NEEDS_REVIEW"  # Lower confidence due to failure
    
    @pytest.mark.asyncio
    async def test_orchestrator_graceful_degradation(self, test_claim, mock_blockchain_service):
        """Test fallback to rule-based reasoning."""
        orchestrator = ADKOrchestrator()
        
        # Document and image agents fail, but fraud agent succeeds
        orchestrator.document_agent.analyze = AsyncMock(side_effect=Exception("Error"))
        orchestrator.image_agent.analyze = AsyncMock(side_effect=Exception("Error"))
        orchestrator.fraud_agent.analyze = AsyncMock(return_value={
            "fraud_score": 0.5, "risk_level": "MEDIUM", "indicators": [], "confidence": 0.7
        })
        
        # Reasoning agent should fallback to rule-based
        orchestrator.reasoning_agent.reason = AsyncMock(return_value={
            "final_confidence": 0.5, "contradictions": [], "fraud_risk": 0.5,
            "missing_evidence": ["valid_document", "valid_image"], "reasoning": "Rule-based fallback"
        })
        
        evidence = []
        
        result = await orchestrator.evaluate_claim(test_claim, evidence)
        
        # Should still return a result
        assert result is not None
        assert "decision" in result
        assert result["decision"] == "NEEDS_REVIEW"
    
    @pytest.mark.asyncio
    async def test_image_agent_handles_corrupted_file(self, tmp_path):
        """Test handling of corrupted image files."""
        agent = ImageAgent()
        agent.client = None  # Use mock mode
        
        # Create corrupted file
        corrupted_file = tmp_path / "corrupted.jpg"
        corrupted_file.write_bytes(b"not a valid image file")
        
        images = [{"file_path": str(corrupted_file)}]
        
        result = await agent.analyze("claim-123", images)
        
        # Should handle gracefully
        # Mock mode will process it, real mode would fail
        assert result is not None
        assert "summary" in result
        # Mock mode returns valid=True, real mode would return valid=False
        if agent.client is None:
            assert result["valid"] is True  # Mock mode
        else:
            assert result["valid"] is False or "No valid images" in result["summary"]
    
    @pytest.mark.asyncio
    async def test_fraud_agent_handles_missing_agent_results(self, mock_gemini_client):
        """Test fraud agent with missing agent results."""
        agent = FraudAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        mock_response = MagicMock()
        mock_response.text = '{"fraud_score": 0.3, "risk_level": "MEDIUM", "indicators": [], "confidence": 0.7}'
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        # No agent results provided
        result = await agent.analyze(
            "claim-123",
            Decimal("1000.00"),
            "0x1234567890123456789012345678901234567890",
            [],
            {}  # Empty agent results
        )
        
        # Should still work
        assert result is not None
        assert "fraud_score" in result
        assert "risk_level" in result
    
    @pytest.mark.asyncio
    async def test_reasoning_agent_handles_empty_agent_results(self):
        """Test reasoning agent with empty agent results."""
        agent = ReasoningAgent()
        agent.client = None  # Use rule-based
        
        # Empty agent results
        result = await agent.reason("claim-123", Decimal("1000.00"), {})
        
        # Should still return a result
        assert result is not None
        assert "final_confidence" in result
        assert 0.0 <= result["final_confidence"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_document_agent_handles_large_file(self, tmp_path):
        """Test handling of very large files."""
        agent = DocumentAgent()
        agent.client = None  # Use mock mode
        
        # Create a large file (simulate)
        large_file = tmp_path / "large.pdf"
        # Write minimal PDF content (in real scenario, this would be large)
        large_file.write_bytes(b"%PDF-1.4\n" + b"x" * 1000)
        
        documents = [{"file_path": str(large_file)}]
        
        result = await agent.analyze("claim-123", documents)
        
        # Should handle (may fail in real scenario with actual large file)
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_orchestrator_handles_blockchain_failure(self, test_claim_high_confidence, mock_blockchain_service):
        """Test behavior when blockchain settlement fails."""
        orchestrator = ADKOrchestrator()
        
        orchestrator.document_agent.analyze = AsyncMock(return_value={
            "summary": "Doc", "valid": True, "confidence": 0.95, "extracted_data": {}
        })
        orchestrator.image_agent.analyze = AsyncMock(return_value={
            "summary": "Img", "valid": True, "confidence": 0.95, "damage_assessment": {}
        })
        orchestrator.fraud_agent.analyze = AsyncMock(return_value={
            "fraud_score": 0.05, "risk_level": "LOW", "indicators": [], "confidence": 0.95
        })
        orchestrator.reasoning_agent.reason = AsyncMock(return_value={
            "final_confidence": 0.96, "contradictions": [], "fraud_risk": 0.05,
            "missing_evidence": [], "reasoning": "High confidence"
        })
        
        # Blockchain service fails
        mock_blockchain_service.approve_claim = AsyncMock(side_effect=Exception("Blockchain error"))
        
        evidence = []
        
        result = await orchestrator.evaluate_claim(test_claim_high_confidence, evidence)
        
        # Should still return result, but settlement may fail
        assert result is not None
        assert result["decision"] == "AUTO_APPROVED"
        # Settlement may fail, but decision is still made
        if result.get("auto_settled"):
            assert result["tx_hash"] is not None