"""
Performance tests for Gemini AI agents.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch
from decimal import Decimal

from src.agent.adk_agents.orchestrator import ADKOrchestrator


@pytest.mark.slow
class TestPerformance:
    """Performance test suite."""
    
    @pytest.mark.asyncio
    async def test_agent_response_time(self, sample_pdf_file):
        """Measure agent response times."""
        from src.agent.agents.document_agent import DocumentAgent
        
        agent = DocumentAgent()
        agent.client = None  # Use mock for speed
        
        documents = [{"file_path": sample_pdf_file}]
        
        start_time = time.time()
        result = await agent.analyze("claim-123", documents)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert result is not None
        # Mock should be fast (< 1 second)
        assert response_time < 1.0
    
    @pytest.mark.asyncio
    async def test_orchestrator_parallel_performance(self, test_claim_with_evidence, mock_blockchain_service):
        """Measure parallel execution performance."""
        orchestrator = ADKOrchestrator()
        
        import asyncio
        call_times = {}
        
        # Simulate agent delays
        async def delayed_document(*args, **kwargs):
            call_times["document_start"] = asyncio.get_event_loop().time()
            await asyncio.sleep(0.1)
            call_times["document_end"] = asyncio.get_event_loop().time()
            return {"summary": "Doc", "valid": True, "confidence": 0.9, "extracted_data": {}}
        
        async def delayed_image(*args, **kwargs):
            call_times["image_start"] = asyncio.get_event_loop().time()
            await asyncio.sleep(0.1)
            call_times["image_end"] = asyncio.get_event_loop().time()
            return {"summary": "Img", "valid": True, "confidence": 0.85, "damage_assessment": {}}
        
        orchestrator.document_agent.analyze = delayed_document
        orchestrator.image_agent.analyze = delayed_image
        orchestrator.fraud_agent.analyze = AsyncMock(return_value={
            "fraud_score": 0.1, "risk_level": "LOW", "indicators": [], "confidence": 0.9
        })
        orchestrator.reasoning_agent.reason = AsyncMock(return_value={
            "final_confidence": 0.9, "contradictions": [], "fraud_risk": 0.1,
            "missing_evidence": [], "reasoning": "Good"
        })
        
        evidence = test_claim_with_evidence.evidence
        
        result = await orchestrator.evaluate_claim(test_claim_with_evidence, evidence)
        
        # Verify parallel execution: both agents should start at roughly the same time
        # (within 0.05s of each other)
        if "document_start" in call_times and "image_start" in call_times:
            start_diff = abs(call_times["document_start"] - call_times["image_start"])
            assert start_diff < 0.05, f"Agents started {start_diff:.3f}s apart, expected parallel execution"
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_api_call_efficiency(self, test_claim_with_evidence, mock_blockchain_service):
        """Measure number of API calls per evaluation."""
        orchestrator = ADKOrchestrator()
        
        call_count = {"document": 0, "image": 0, "fraud": 0, "reasoning": 0}
        
        async def track_document(*args, **kwargs):
            call_count["document"] += 1
            return {"summary": "Doc", "valid": True, "confidence": 0.9, "extracted_data": {}}
        
        async def track_image(*args, **kwargs):
            call_count["image"] += 1
            return {"summary": "Img", "valid": True, "confidence": 0.85, "damage_assessment": {}}
        
        async def track_fraud(*args, **kwargs):
            call_count["fraud"] += 1
            return {"fraud_score": 0.1, "risk_level": "LOW", "indicators": [], "confidence": 0.9}
        
        async def track_reasoning(*args, **kwargs):
            call_count["reasoning"] += 1
            return {
                "final_confidence": 0.9, "contradictions": [], "fraud_risk": 0.1,
                "missing_evidence": [], "reasoning": "Good"
            }
        
        orchestrator.document_agent.analyze = track_document
        orchestrator.image_agent.analyze = track_image
        orchestrator.fraud_agent.analyze = track_fraud
        orchestrator.reasoning_agent.reason = track_reasoning
        
        evidence = test_claim_with_evidence.evidence
        
        await orchestrator.evaluate_claim(test_claim_with_evidence, evidence)
        
        # Each agent should be called exactly once
        assert call_count["document"] == 1
        assert call_count["image"] == 1
        assert call_count["fraud"] == 1
        assert call_count["reasoning"] == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_evaluations(self, test_db, test_claimant, mock_blockchain_service):
        """Test system under concurrent load."""
        from src.models import Claim
        import uuid
        
        orchestrator = ADKOrchestrator()
        
        # Mock agents for speed
        orchestrator.document_agent.analyze = AsyncMock(return_value={
            "summary": "Doc", "valid": True, "confidence": 0.9, "extracted_data": {}
        })
        orchestrator.image_agent.analyze = AsyncMock(return_value={
            "summary": "Img", "valid": True, "confidence": 0.85, "damage_assessment": {}
        })
        orchestrator.fraud_agent.analyze = AsyncMock(return_value={
            "fraud_score": 0.1, "risk_level": "LOW", "indicators": [], "confidence": 0.9
        })
        orchestrator.reasoning_agent.reason = AsyncMock(return_value={
            "final_confidence": 0.9, "contradictions": [], "fraud_risk": 0.1,
            "missing_evidence": [], "reasoning": "Good"
        })
        
        # Create multiple claims
        wallet = test_db.query(test_claimant.__class__).first()
        claims = []
        for i in range(5):
            claim = Claim(
                id=str(uuid.uuid4()),
                claimant_address="0x1234567890123456789012345678901234567890",
                claim_amount=Decimal("1000.00"),
                status="SUBMITTED",
                processing_costs=Decimal("0.00")
            )
            test_db.add(claim)
            claims.append(claim)
        test_db.commit()
        
        # Evaluate all claims concurrently
        async def evaluate_claim_async(claim):
            return await orchestrator.evaluate_claim(claim, [])
        
        start_time = time.time()
        results = await asyncio.gather(*[evaluate_claim_async(claim) for claim in claims])
        end_time = time.time()
        
        total_time = end_time - start_time
        
        # All should complete successfully
        assert len(results) == 5
        for result in results:
            assert result is not None
            assert "decision" in result
        
        # Concurrent execution should be reasonably fast
        # 5 evaluations should complete in < 2 seconds (with mocks)
        assert total_time < 2.0
    
    @pytest.mark.asyncio
    async def test_evaluation_timeout_threshold(self, test_claim_with_evidence, mock_blockchain_service):
        """Test that evaluations complete within acceptable time."""
        orchestrator = ADKOrchestrator()
        
        # Simulate realistic delays
        async def realistic_document(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms delay
            return {"summary": "Doc", "valid": True, "confidence": 0.9, "extracted_data": {}}
        
        async def realistic_image(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms delay
            return {"summary": "Img", "valid": True, "confidence": 0.85, "damage_assessment": {}}
        
        orchestrator.document_agent.analyze = realistic_document
        orchestrator.image_agent.analyze = realistic_image
        orchestrator.fraud_agent.analyze = AsyncMock(return_value={
            "fraud_score": 0.1, "risk_level": "LOW", "indicators": [], "confidence": 0.9
        })
        orchestrator.reasoning_agent.reason = AsyncMock(return_value={
            "final_confidence": 0.9, "contradictions": [], "fraud_risk": 0.1,
            "missing_evidence": [], "reasoning": "Good"
        })
        
        evidence = test_claim_with_evidence.evidence
        
        start_time = time.time()
        result = await orchestrator.evaluate_claim(test_claim_with_evidence, evidence)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Should complete within 30 seconds (realistic threshold)
        assert execution_time < 30.0
        assert result is not None