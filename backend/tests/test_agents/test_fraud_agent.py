"""
Unit tests for FraudAgent.
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from src.agent.agents.fraud_agent import FraudAgent


@pytest.mark.unit
class TestFraudAgent:
    """Test suite for FraudAgent."""
    
    def test_fraud_agent_initialization(self):
        """Verify agent initialization."""
        with patch.dict(os.environ, {"GOOGLE_AI_API_KEY": "test-api-key"}):
            agent = FraudAgent()
            
            assert agent.api_key == "test-api-key"
            assert agent.model_name == "gemini-2.0-flash"
            # Client may or may not be initialized depending on GEMINI_AVAILABLE
            assert agent is not None
    
    def test_fraud_agent_initialization_without_api_key(self):
        """Verify fallback when no API key."""
        with patch.dict(os.environ, {}, clear=True):
            agent = FraudAgent()
            
            assert agent.api_key is None
            assert agent.client is None
    
    @pytest.mark.asyncio
    async def test_analyze_low_risk_claim(self, mock_gemini_client):
        """Test low fraud risk detection."""
        agent = FraudAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        mock_response = MagicMock()
        mock_response.text = """{
            "fraud_score": 0.05,
            "risk_level": "LOW",
            "indicators": [],
            "confidence": 0.9,
            "notes": "Claim appears legitimate"
        }"""
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        result = await agent.analyze(
            "claim-123",
            Decimal("1000.00"),
            "0x1234567890123456789012345678901234567890",
            [],
            {}
        )
        
        assert result["fraud_score"] < 0.3
        assert result["risk_level"] == "LOW"
        assert len(result["indicators"]) == 0
    
    @pytest.mark.asyncio
    async def test_analyze_high_risk_claim(self, mock_gemini_client):
        """Test high fraud risk detection."""
        agent = FraudAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        mock_response = MagicMock()
        mock_response.text = """{
            "fraud_score": 0.85,
            "risk_level": "HIGH",
            "indicators": ["Amount mismatch", "Suspicious timing", "Inconsistent evidence"],
            "confidence": 0.9,
            "notes": "Multiple fraud indicators detected"
        }"""
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        result = await agent.analyze(
            "claim-123",
            Decimal("10000.00"),
            "0x1234567890123456789012345678901234567890",
            [],
            {}
        )
        
        assert result["fraud_score"] >= 0.7
        assert result["risk_level"] == "HIGH"
        assert len(result["indicators"]) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_with_contradictions(self, mock_gemini_client):
        """Test detection of inconsistencies."""
        agent = FraudAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Create contradictory agent results
        agent_results = {
            "document": {
                "extracted_data": {"amount": 1000.0},
                "valid": True
            },
            "image": {
                "damage_assessment": {"estimated_cost": 5000.0},
                "valid": True
            }
        }
        
        mock_response = MagicMock()
        mock_response.text = """{
            "fraud_score": 0.6,
            "risk_level": "MEDIUM",
            "indicators": ["Significant discrepancy between document amount and image assessment"],
            "confidence": 0.85,
            "notes": "Contradiction detected between evidence sources"
        }"""
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        result = await agent.analyze(
            "claim-123",
            Decimal("1000.00"),
            "0x1234567890123456789012345678901234567890",
            [],
            agent_results
        )
        
        assert result["risk_level"] in ["MEDIUM", "HIGH"]
        assert len(result["indicators"]) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_amount_mismatch(self, mock_gemini_client):
        """Test detection of amount discrepancies."""
        agent = FraudAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Claim amount doesn't match document amount
        agent_results = {
            "document": {
                "extracted_data": {"amount": 2000.0},
                "valid": True
            }
        }
        
        mock_response = MagicMock()
        mock_response.text = """{
            "fraud_score": 0.5,
            "risk_level": "MEDIUM",
            "indicators": ["Claim amount ($1000.00) differs from document amount ($2000.00)"],
            "confidence": 0.8,
            "notes": "Amount mismatch detected"
        }"""
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        result = await agent.analyze(
            "claim-123",
            Decimal("1000.00"),  # Different from document amount
            "0x1234567890123456789012345678901234567890",
            [],
            agent_results
        )
        
        assert result["risk_level"] in ["MEDIUM", "HIGH"]
        assert any("amount" in ind.lower() or "mismatch" in ind.lower() for ind in result["indicators"])
    
    @pytest.mark.asyncio
    async def test_analyze_timing_patterns(self, mock_gemini_client):
        """Test suspicious timing detection."""
        agent = FraudAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        mock_response = MagicMock()
        mock_response.text = """{
            "fraud_score": 0.4,
            "risk_level": "MEDIUM",
            "indicators": ["Unusual claim timing pattern"],
            "confidence": 0.75,
            "notes": "Timing pattern may indicate fraud"
        }"""
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        result = await agent.analyze(
            "claim-123",
            Decimal("5000.00"),
            "0x1234567890123456789012345678901234567890",
            [],
            {}
        )
        
        assert result["risk_level"] in ["MEDIUM", "HIGH"]
    
    @pytest.mark.asyncio
    async def test_analyze_uses_agent_results(self, mock_gemini_client):
        """Verify integration with document/image results."""
        agent = FraudAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        agent_results = {
            "document": {
                "extracted_data": {
                    "amount": 3500.0,
                    "vendor": "Auto Shop",
                    "document_type": "invoice"
                },
                "valid": True,
                "confidence": 0.9
            },
            "image": {
                "damage_assessment": {
                    "damage_type": "collision",
                    "severity": "moderate",
                    "estimated_cost": 3500.0
                },
                "valid": True,
                "confidence": 0.85
            }
        }
        
        mock_response = MagicMock()
        mock_response.text = """{
            "fraud_score": 0.1,
            "risk_level": "LOW",
            "indicators": [],
            "confidence": 0.9,
            "notes": "Evidence is consistent"
        }"""
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        result = await agent.analyze(
            "claim-123",
            Decimal("3500.00"),
            "0x1234567890123456789012345678901234567890",
            [],
            agent_results
        )
        
        # Verify context was built with agent results
        call_args = mock_gemini_client.generate_content_async.call_args
        assert call_args is not None
        context = call_args[0][0] if call_args[0] else ""
        assert "Document Analysis" in context or "Image Analysis" in context
    
    @pytest.mark.asyncio
    async def test_analyze_returns_indicators(self, mock_gemini_client):
        """Verify fraud indicators list."""
        agent = FraudAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        mock_response = MagicMock()
        mock_response.text = """{
            "fraud_score": 0.7,
            "risk_level": "HIGH",
            "indicators": ["Indicator 1", "Indicator 2", "Indicator 3"],
            "confidence": 0.9,
            "notes": "Multiple indicators"
        }"""
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        result = await agent.analyze(
            "claim-123",
            Decimal("5000.00"),
            "0x1234567890123456789012345678901234567890",
            [],
            {}
        )
        
        assert "indicators" in result
        assert isinstance(result["indicators"], list)
        assert len(result["indicators"]) == 3
    
    @pytest.mark.asyncio
    async def test_analyze_calculates_risk_level(self, mock_gemini_client):
        """Test risk level calculation (LOW/MEDIUM/HIGH)."""
        agent = FraudAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Test LOW risk
        mock_response = MagicMock()
        mock_response.text = '{"fraud_score": 0.1, "risk_level": "LOW", "indicators": [], "confidence": 0.9}'
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        result = await agent.analyze("claim-123", Decimal("1000.00"), "0x123", [], {})
        assert result["risk_level"] == "LOW"
        
        # Test MEDIUM risk
        mock_response.text = '{"fraud_score": 0.5, "risk_level": "MEDIUM", "indicators": ["Indicator"], "confidence": 0.9}'
        result = await agent.analyze("claim-123", Decimal("1000.00"), "0x123", [], {})
        assert result["risk_level"] == "MEDIUM"
        
        # Test HIGH risk
        mock_response.text = '{"fraud_score": 0.8, "risk_level": "HIGH", "indicators": ["Indicator"], "confidence": 0.9}'
        result = await agent.analyze("claim-123", Decimal("1000.00"), "0x123", [], {})
        assert result["risk_level"] == "HIGH"
    
    @pytest.mark.asyncio
    async def test_analyze_api_error_handling(self, mock_gemini_client):
        """Test API failure scenarios."""
        agent = FraudAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Simulate API error
        mock_gemini_client.generate_content_async = AsyncMock(side_effect=Exception("API Error"))
        
        result = await agent.analyze(
            "claim-123",
            Decimal("1000.00"),
            "0x1234567890123456789012345678901234567890",
            [],
            {}
        )
        
        # Should handle error gracefully with neutral values
        assert result["fraud_score"] == 0.5  # Neutral on error
        assert result["risk_level"] == "MEDIUM"
        assert "error" in result["indicators"][0].lower()
    
    @pytest.mark.asyncio
    async def test_analyze_mock_analysis_fallback(self):
        """Verify mock analysis when API unavailable."""
        agent = FraudAgent()
        agent.client = None
        
        result = await agent.analyze(
            "claim-123",
            Decimal("1000.00"),
            "0x1234567890123456789012345678901234567890",
            [],
            {}
        )
        
        assert result["fraud_score"] == 0.05
        assert result["risk_level"] == "LOW"
        assert len(result["indicators"]) == 0
        assert "mock" in result["check_id"].lower()
    
    @pytest.mark.asyncio
    async def test_analyze_handles_malformed_json_response(self, mock_gemini_client):
        """Test handling of malformed JSON from API."""
        agent = FraudAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Return non-JSON text
        mock_response = MagicMock()
        mock_response.text = "The claim appears to have some inconsistencies that warrant review."
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        result = await agent.analyze(
            "claim-123",
            Decimal("1000.00"),
            "0x1234567890123456789012345678901234567890",
            [],
            {}
        )
        
        # Should fallback to text parsing
        assert result is not None
        assert "fraud_score" in result
        assert "risk_level" in result
        assert 0.0 <= result["fraud_score"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_analyze_builds_context_correctly(self, mock_gemini_client):
        """Test that context is built correctly with all information."""
        agent = FraudAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        agent_results = {
            "document": {
                "extracted_data": {"amount": 2000.0, "vendor": "Shop"}
            },
            "image": {
                "damage_assessment": {"estimated_cost": 2000.0}
            }
        }
        
        mock_response = MagicMock()
        mock_response.text = '{"fraud_score": 0.1, "risk_level": "LOW", "indicators": [], "confidence": 0.9}'
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        await agent.analyze(
            "claim-123",
            Decimal("2000.00"),
            "0x1234567890123456789012345678901234567890",
            [{"file_type": "document", "file_path": "/path/to/doc.pdf"}],
            agent_results
        )
        
        # Verify context includes all relevant information
        call_args = mock_gemini_client.generate_content_async.call_args
        context = call_args[0][0] if call_args[0] else ""
        assert "claim-123" in context
        # Amount may be formatted as $2,000.00 or 2000.00
        assert "2000" in context or "2,000" in context
        assert "0x1234567890123456789012345678901234567890" in context
    
    @pytest.mark.asyncio
    @pytest.mark.real_api
    async def test_analyze_with_real_api(self, real_gemini_client):
        """Test fraud analysis with real Gemini API."""
        if not real_gemini_client:
            pytest.skip("Real Gemini API not available")
        
        agent = FraudAgent(api_key=os.getenv("GOOGLE_AI_API_KEY"))
        agent.client = real_gemini_client
        
        result = await agent.analyze(
            "claim-123",
            Decimal("1000.00"),
            "0x1234567890123456789012345678901234567890",
            [],
            {}
        )
        
        assert result is not None
        assert "fraud_score" in result
        assert "risk_level" in result
        assert 0.0 <= result["fraud_score"] <= 1.0
        assert result["risk_level"] in ["LOW", "MEDIUM", "HIGH"]