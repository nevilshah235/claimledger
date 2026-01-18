"""
Unit tests for ReasoningAgent.
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from src.agent.agents.reasoning_agent import ReasoningAgent


@pytest.mark.unit
class TestReasoningAgent:
    """Test suite for ReasoningAgent."""
    
    def test_reasoning_agent_initialization(self):
        """Verify agent initialization."""
        with patch.dict(os.environ, {"GOOGLE_AI_API_KEY": "test-api-key"}):
            agent = ReasoningAgent()
            
            assert agent.api_key == "test-api-key"
            assert agent.model_name == "gemini-2.0-flash"
            # Client may or may not be initialized depending on GEMINI_AVAILABLE
            assert agent is not None
    
    def test_reasoning_agent_initialization_without_api_key(self):
        """Verify fallback when no API key."""
        with patch.dict(os.environ, {}, clear=True):
            agent = ReasoningAgent()
            
            assert agent.api_key is None
            assert agent.client is None
    
    @pytest.mark.asyncio
    async def test_reason_with_all_agents_valid(self, mock_gemini_client):
        """Test reasoning with all valid agent results."""
        agent = ReasoningAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        agent_results = {
            "document": {
                "valid": True,
                "confidence": 0.9,
                "extracted_data": {
                    "amount": 3500.0,
                    "vendor": "Auto Shop",
                    "document_type": "invoice"
                }
            },
            "image": {
                "valid": True,
                "confidence": 0.85,
                "damage_assessment": {
                    "damage_type": "collision",
                    "severity": "moderate",
                    "estimated_cost": 3500.0
                }
            },
            "fraud": {
                "fraud_score": 0.1,
                "risk_level": "LOW",
                "confidence": 0.9
            }
        }
        
        mock_response = MagicMock()
        mock_response.text = """{
            "final_confidence": 0.92,
            "contradictions": [],
            "fraud_risk": 0.1,
            "missing_evidence": [],
            "reasoning": "All evidence is consistent and valid",
            "evidence_gaps": []
        }"""
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        result = await agent.reason("claim-123", Decimal("3500.00"), agent_results)
        
        assert result["final_confidence"] > 0.9
        assert len(result["contradictions"]) == 0
        assert result["fraud_risk"] < 0.3
        assert len(result["missing_evidence"]) == 0
    
    @pytest.mark.asyncio
    async def test_reason_detects_contradictions(self, mock_gemini_client):
        """Test contradiction detection."""
        agent = ReasoningAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Create contradictory agent results
        agent_results = {
            "document": {
                "valid": True,
                "confidence": 0.9,
                "extracted_data": {"amount": 1000.0}
            },
            "image": {
                "valid": True,
                "confidence": 0.85,
                "damage_assessment": {"estimated_cost": 5000.0}
            },
            "fraud": {
                "fraud_score": 0.5,
                "risk_level": "MEDIUM",
                "confidence": 0.8
            }
        }
        
        mock_response = MagicMock()
        mock_response.text = """{
            "final_confidence": 0.7,
            "contradictions": ["Document amount ($1000.00) differs significantly from image estimated cost ($5000.00)"],
            "fraud_risk": 0.5,
            "missing_evidence": [],
            "reasoning": "Contradiction detected between evidence sources",
            "evidence_gaps": []
        }"""
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        result = await agent.reason("claim-123", Decimal("1000.00"), agent_results)
        
        assert len(result["contradictions"]) > 0
        assert result["final_confidence"] < 0.9  # Lower confidence due to contradiction
    
    @pytest.mark.asyncio
    async def test_reason_calculates_confidence(self, mock_gemini_client):
        """Verify final confidence calculation."""
        agent = ReasoningAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        agent_results = {
            "document": {"valid": True, "confidence": 0.9},
            "image": {"valid": True, "confidence": 0.85},
            "fraud": {"fraud_score": 0.1, "confidence": 0.9}
        }
        
        mock_response = MagicMock()
        mock_response.text = '{"final_confidence": 0.88, "contradictions": [], "fraud_risk": 0.1, "missing_evidence": [], "reasoning": "Good confidence", "evidence_gaps": []}'
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        result = await agent.reason("claim-123", Decimal("1000.00"), agent_results)
        
        assert 0.0 <= result["final_confidence"] <= 1.0
        assert result["final_confidence"] == 0.88
    
    @pytest.mark.asyncio
    async def test_reason_identifies_missing_evidence(self, mock_gemini_client):
        """Test missing evidence detection."""
        agent = ReasoningAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Missing document evidence
        agent_results = {
            "image": {"valid": True, "confidence": 0.85},
            "fraud": {"fraud_score": 0.2, "confidence": 0.8}
        }
        
        mock_response = MagicMock()
        mock_response.text = """{
            "final_confidence": 0.6,
            "contradictions": [],
            "fraud_risk": 0.2,
            "missing_evidence": ["valid_document"],
            "reasoning": "Document evidence is missing",
            "evidence_gaps": ["No valid document verification"]
        }"""
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        result = await agent.reason("claim-123", Decimal("1000.00"), agent_results)
        
        assert len(result["missing_evidence"]) > 0
        assert "document" in result["missing_evidence"][0].lower() or "valid_document" in result["missing_evidence"]
    
    @pytest.mark.asyncio
    async def test_reason_assesses_fraud_risk(self, mock_gemini_client):
        """Test fraud risk aggregation."""
        agent = ReasoningAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        agent_results = {
            "document": {"valid": True, "confidence": 0.9},
            "image": {"valid": True, "confidence": 0.85},
            "fraud": {"fraud_score": 0.7, "risk_level": "HIGH", "confidence": 0.9}
        }
        
        mock_response = MagicMock()
        mock_response.text = """{
            "final_confidence": 0.5,
            "contradictions": [],
            "fraud_risk": 0.7,
            "missing_evidence": [],
            "reasoning": "High fraud risk detected",
            "evidence_gaps": []
        }"""
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        result = await agent.reason("claim-123", Decimal("1000.00"), agent_results)
        
        assert result["fraud_risk"] >= 0.7
        assert result["final_confidence"] < 0.7  # Lower confidence due to high fraud risk
    
    @pytest.mark.asyncio
    async def test_reason_with_partial_evidence(self, mock_gemini_client):
        """Test reasoning with incomplete evidence."""
        agent = ReasoningAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Only document evidence, no image
        agent_results = {
            "document": {"valid": True, "confidence": 0.9},
            "fraud": {"fraud_score": 0.2, "confidence": 0.8}
        }
        
        mock_response = MagicMock()
        mock_response.text = """{
            "final_confidence": 0.65,
            "contradictions": [],
            "fraud_risk": 0.2,
            "missing_evidence": ["valid_image"],
            "reasoning": "Image evidence is missing",
            "evidence_gaps": ["No valid image analysis"]
        }"""
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        result = await agent.reason("claim-123", Decimal("1000.00"), agent_results)
        
        assert result["final_confidence"] < 0.8  # Lower confidence with partial evidence
        assert len(result["missing_evidence"]) > 0
    
    @pytest.mark.asyncio
    async def test_reason_rule_based_fallback(self):
        """Test fallback to rule-based reasoning."""
        agent = ReasoningAgent()
        agent.client = None  # No API, should use rule-based
        
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
        
        assert "final_confidence" in result
        assert "contradictions" in result
        assert "fraud_risk" in result
        assert "reasoning" in result
        assert 0.0 <= result["final_confidence"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_reason_api_error_handling(self, mock_gemini_client):
        """Test API failure scenarios."""
        agent = ReasoningAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Simulate API error
        mock_gemini_client.generate_content_async = AsyncMock(side_effect=Exception("API Error"))
        
        agent_results = {
            "document": {"valid": True, "confidence": 0.9},
            "image": {"valid": True, "confidence": 0.85},
            "fraud": {"fraud_score": 0.1, "confidence": 0.9}
        }
        
        result = await agent.reason("claim-123", Decimal("1000.00"), agent_results)
        
        # Should fallback to rule-based reasoning
        assert "final_confidence" in result
        assert 0.0 <= result["final_confidence"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_reason_evidence_gaps(self, mock_gemini_client):
        """Test evidence gap identification."""
        agent = ReasoningAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Incomplete evidence
        agent_results = {
            "document": {"valid": False, "confidence": 0.3},
            "image": {"valid": False, "confidence": 0.3}
        }
        
        mock_response = MagicMock()
        mock_response.text = """{
            "final_confidence": 0.4,
            "contradictions": [],
            "fraud_risk": 0.3,
            "missing_evidence": ["valid_document", "valid_image"],
            "reasoning": "Both document and image evidence are invalid",
            "evidence_gaps": ["No valid document verification", "No valid image analysis"]
        }"""
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        result = await agent.reason("claim-123", Decimal("1000.00"), agent_results)
        
        assert len(result["evidence_gaps"]) > 0
        assert result["final_confidence"] < 0.5  # Low confidence with gaps
    
    @pytest.mark.asyncio
    async def test_reason_handles_malformed_json_response(self, mock_gemini_client):
        """Test handling of malformed JSON from API."""
        agent = ReasoningAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        agent_results = {
            "document": {"valid": True, "confidence": 0.9},
            "image": {"valid": True, "confidence": 0.85},
            "fraud": {"fraud_score": 0.1, "confidence": 0.9}
        }
        
        # Return non-JSON text
        mock_response = MagicMock()
        mock_response.text = "The evidence appears consistent and the claim seems valid based on the provided information."
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        result = await agent.reason("claim-123", Decimal("1000.00"), agent_results)
        
        # Should fallback to rule-based reasoning
        assert result is not None
        assert "final_confidence" in result
        assert 0.0 <= result["final_confidence"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_reason_builds_context_correctly(self, mock_gemini_client):
        """Test that context is built correctly with all agent results."""
        agent = ReasoningAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        agent_results = {
            "document": {
                "valid": True,
                "confidence": 0.9,
                "extracted_data": {"amount": 2000.0, "vendor": "Shop"}
            },
            "image": {
                "valid": True,
                "confidence": 0.85,
                "damage_assessment": {"estimated_cost": 2000.0, "severity": "moderate"}
            },
            "fraud": {
                "fraud_score": 0.1,
                "risk_level": "LOW",
                "confidence": 0.9
            }
        }
        
        mock_response = MagicMock()
        mock_response.text = '{"final_confidence": 0.9, "contradictions": [], "fraud_risk": 0.1, "missing_evidence": [], "reasoning": "Good", "evidence_gaps": []}'
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        await agent.reason("claim-123", Decimal("2000.00"), agent_results)
        
        # Verify context includes all agent results
        call_args = mock_gemini_client.generate_content_async.call_args
        context = call_args[0][0] if call_args[0] else ""
        assert "claim-123" in context
        # Amount may be formatted as $2,000.00 or 2000.00
        assert "2000" in context or "2,000" in context
        assert "Document Agent" in context or "document" in context.lower()
        assert "Image Agent" in context or "image" in context.lower()
        assert "Fraud Agent" in context or "fraud" in context.lower()
    
    @pytest.mark.asyncio
    async def test_reason_rule_based_contradiction_detection(self):
        """Test rule-based contradiction detection."""
        agent = ReasoningAgent()
        agent.client = None
        
        # Create contradictory results
        agent_results = {
            "document": {
                "valid": True,
                "confidence": 0.9,
                "extracted_data": {"amount": 1000.0}
            },
            "image": {
                "valid": True,
                "confidence": 0.85,
                "damage_assessment": {"estimated_cost": 5000.0}
            },
            "fraud": {
                "fraud_score": 0.3,
                "risk_level": "MEDIUM",
                "confidence": 0.8
            }
        }
        
        result = await agent.reason("claim-123", Decimal("1000.00"), agent_results)
        
        # Should detect contradiction between amounts
        assert len(result["contradictions"]) > 0
        assert any("amount" in c.lower() or "cost" in c.lower() for c in result["contradictions"])
    
    @pytest.mark.asyncio
    @pytest.mark.real_api
    async def test_reason_with_real_api(self, real_gemini_client):
        """Test reasoning with real Gemini API."""
        if not real_gemini_client:
            pytest.skip("Real Gemini API not available")
        
        agent = ReasoningAgent(api_key=os.getenv("GOOGLE_AI_API_KEY"))
        agent.client = real_gemini_client
        
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