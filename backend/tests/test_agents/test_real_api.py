"""
Real API tests for Gemini AI agents.
These tests require GOOGLE_AI_API_KEY to be set.
"""

import pytest
import os
from decimal import Decimal

from src.agent.agents.document_agent import DocumentAgent
from src.agent.agents.image_agent import ImageAgent
from src.agent.agents.fraud_agent import FraudAgent
from src.agent.agents.reasoning_agent import ReasoningAgent


@pytest.mark.real_api
@pytest.mark.slow
class TestRealGeminiAPI:
    """Test suite for real Gemini API integration."""
    
    @pytest.fixture(autouse=True)
    def check_api_key(self):
        """Skip tests if API key is not available."""
        if not os.getenv("GOOGLE_AI_API_KEY"):
            pytest.skip("GOOGLE_AI_API_KEY not set, skipping real API tests")
    
    @pytest.mark.asyncio
    async def test_document_agent_real_api(self, sample_pdf_file):
        """Test DocumentAgent with real Gemini API."""
        agent = DocumentAgent(api_key=os.getenv("GOOGLE_AI_API_KEY"))
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        assert result is not None
        assert "summary" in result
        assert "confidence" in result
        assert "extracted_data" in result
        assert 0.0 <= result["confidence"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_image_agent_real_api(self, sample_damage_photo):
        """Test ImageAgent with real Gemini API."""
        agent = ImageAgent(api_key=os.getenv("GOOGLE_AI_API_KEY"))
        
        images = [{"file_path": sample_damage_photo}]
        
        result = await agent.analyze("claim-123", images)
        
        assert result is not None
        assert "summary" in result
        assert "confidence" in result
        assert "damage_assessment" in result
        assert 0.0 <= result["confidence"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_fraud_agent_real_api(self):
        """Test FraudAgent with real Gemini API."""
        agent = FraudAgent(api_key=os.getenv("GOOGLE_AI_API_KEY"))
        
        agent_results = {
            "document": {
                "extracted_data": {"amount": 2000.0},
                "valid": True
            },
            "image": {
                "damage_assessment": {"estimated_cost": 2000.0},
                "valid": True
            }
        }
        
        result = await agent.analyze(
            "claim-123",
            Decimal("2000.00"),
            "0x1234567890123456789012345678901234567890",
            [],
            agent_results
        )
        
        assert result is not None
        assert "fraud_score" in result
        assert "risk_level" in result
        assert 0.0 <= result["fraud_score"] <= 1.0
        assert result["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
    
    @pytest.mark.asyncio
    async def test_reasoning_agent_real_api(self):
        """Test ReasoningAgent with real Gemini API."""
        agent = ReasoningAgent(api_key=os.getenv("GOOGLE_AI_API_KEY"))
        
        agent_results = {
            "document": {
                "valid": True,
                "confidence": 0.9,
                "extracted_data": {"amount": 2000.0}
            },
            "image": {
                "valid": True,
                "confidence": 0.85,
                "damage_assessment": {"estimated_cost": 2000.0}
            },
            "fraud": {
                "fraud_score": 0.1,
                "risk_level": "LOW",
                "confidence": 0.9
            }
        }
        
        result = await agent.reason("claim-123", Decimal("2000.00"), agent_results)
        
        assert result is not None
        assert "final_confidence" in result
        assert "contradictions" in result
        assert "fraud_risk" in result
        assert 0.0 <= result["final_confidence"] <= 1.0
        assert 0.0 <= result["fraud_risk"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_all_agents_integration_real_api(self, sample_pdf_file, sample_damage_photo):
        """Test all agents working together with real API."""
        doc_agent = DocumentAgent(api_key=os.getenv("GOOGLE_AI_API_KEY"))
        img_agent = ImageAgent(api_key=os.getenv("GOOGLE_AI_API_KEY"))
        fraud_agent = FraudAgent(api_key=os.getenv("GOOGLE_AI_API_KEY"))
        reasoning_agent = ReasoningAgent(api_key=os.getenv("GOOGLE_AI_API_KEY"))
        
        # Document analysis
        doc_result = await doc_agent.analyze("claim-123", [{"file_path": sample_pdf_file}])
        assert doc_result is not None
        
        # Image analysis
        img_result = await img_agent.analyze("claim-123", [{"file_path": sample_damage_photo}])
        assert img_result is not None
        
        # Fraud analysis
        agent_results = {
            "document": doc_result,
            "image": img_result
        }
        fraud_result = await fraud_agent.analyze(
            "claim-123",
            Decimal("2000.00"),
            "0x1234567890123456789012345678901234567890",
            [],
            agent_results
        )
        assert fraud_result is not None
        
        # Reasoning
        all_results = {
            "document": doc_result,
            "image": img_result,
            "fraud": fraud_result
        }
        reasoning_result = await reasoning_agent.reason("claim-123", Decimal("2000.00"), all_results)
        assert reasoning_result is not None
        assert "final_confidence" in reasoning_result