"""
Unit tests for ImageAgent.
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.agent.agents.image_agent import ImageAgent


@pytest.mark.unit
class TestImageAgent:
    """Test suite for ImageAgent."""
    
    def test_image_agent_initialization(self):
        """Verify agent initialization."""
        with patch.dict(os.environ, {"GOOGLE_AI_API_KEY": "test-api-key"}):
            agent = ImageAgent()
            
            assert agent.api_key == "test-api-key"
            assert agent.model_name == "gemini-2.0-flash"
            # Client may or may not be initialized depending on GEMINI_AVAILABLE
            assert agent is not None
    
    def test_image_agent_initialization_without_api_key(self):
        """Verify fallback when no API key."""
        with patch.dict(os.environ, {}, clear=True):
            agent = ImageAgent()
            
            assert agent.api_key is None
            assert agent.client is None
    
    @pytest.mark.asyncio
    async def test_analyze_with_empty_images_list(self):
        """Test with no images provided."""
        agent = ImageAgent()
        
        result = await agent.analyze("claim-123", [])
        
        assert result["summary"] == "No images provided"
        assert result["valid"] is False
        assert result["confidence"] == 0.0
        assert result["damage_assessment"] == {}
        assert result["analysis_id"] is None
    
    @pytest.mark.asyncio
    async def test_analyze_with_missing_file(self, tmp_path):
        """Test handling of non-existent file paths."""
        agent = ImageAgent()
        
        images = [{"file_path": str(tmp_path / "nonexistent.jpg")}]
        
        result = await agent.analyze("claim-123", images)
        
        # When file doesn't exist, it's skipped in the loop
        # If no results, should return "No valid images could be analyzed"
        # If mock mode is used (client is None), it will use mock_analysis
        assert result is not None
        assert "summary" in result
        if agent.client is None:
            # Mock mode - will return valid result
            assert result["valid"] is True
        else:
            # Real mode - file doesn't exist, so skipped
            assert result["valid"] is False
            assert "No valid images" in result["summary"]
    
    @pytest.mark.asyncio
    async def test_analyze_with_valid_damage_photo_mocked(self, sample_damage_photo, mock_gemini_client):
        """Test damage photo analysis with mocked Gemini API."""
        agent = ImageAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        mock_response = MagicMock()
        mock_response.text = """{
            "damage_type": "collision",
            "affected_parts": ["front_bumper", "hood"],
            "severity": "moderate",
            "estimated_cost": 3500.00,
            "confidence": 0.89,
            "valid": true,
            "notes": "Clear damage visible"
        }"""
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        images = [{"file_path": sample_damage_photo}]
        
        result = await agent.analyze("claim-123", images)
        
        assert result["valid"] is True
        assert result["confidence"] > 0.0
        assert "damage_assessment" in result
        assert result["damage_assessment"]["damage_type"] == "collision"
    
    @pytest.mark.asyncio
    async def test_analyze_detects_damage_type(self, sample_damage_photo, mock_gemini_client):
        """Verify damage type detection (collision, fire, water)."""
        agent = ImageAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Test collision
        mock_response = MagicMock()
        mock_response.text = '{"damage_type": "collision", "affected_parts": ["bumper"], "severity": "moderate", "estimated_cost": 2000.0, "confidence": 0.9, "valid": true}'
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        images = [{"file_path": sample_damage_photo}]
        result = await agent.analyze("claim-123", images)
        
        assert result["damage_assessment"]["damage_type"] == "collision"
        
        # Test fire damage
        mock_response.text = '{"damage_type": "fire", "affected_parts": ["engine"], "severity": "severe", "estimated_cost": 10000.0, "confidence": 0.9, "valid": true}'
        result = await agent.analyze("claim-123", images)
        assert result["damage_assessment"]["damage_type"] == "fire"
        
        # Test water damage
        mock_response.text = '{"damage_type": "water", "affected_parts": ["interior"], "severity": "moderate", "estimated_cost": 5000.0, "confidence": 0.9, "valid": true}'
        result = await agent.analyze("claim-123", images)
        assert result["damage_assessment"]["damage_type"] == "water"
    
    @pytest.mark.asyncio
    async def test_analyze_assesses_severity(self, sample_damage_photo, mock_gemini_client):
        """Test severity assessment (minor, moderate, severe)."""
        agent = ImageAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        severities = ["minor", "moderate", "severe", "total"]
        
        for severity in severities:
            mock_response = MagicMock()
            mock_response.text = f'{{"damage_type": "collision", "affected_parts": ["bumper"], "severity": "{severity}", "estimated_cost": 1000.0, "confidence": 0.9, "valid": true}}'
            mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
            
            images = [{"file_path": sample_damage_photo}]
            result = await agent.analyze("claim-123", images)
            
            assert result["damage_assessment"]["severity"] == severity
    
    @pytest.mark.asyncio
    async def test_analyze_estimates_cost(self, sample_damage_photo, mock_gemini_client):
        """Verify cost estimation from images."""
        agent = ImageAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        mock_response = MagicMock()
        mock_response.text = '{"damage_type": "collision", "affected_parts": ["bumper"], "severity": "moderate", "estimated_cost": 2500.75, "confidence": 0.9, "valid": true}'
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        images = [{"file_path": sample_damage_photo}]
        
        result = await agent.analyze("claim-123", images)
        
        assert result["damage_assessment"]["estimated_cost"] == 2500.75
    
    @pytest.mark.asyncio
    async def test_analyze_multiple_images(self, sample_damage_photo, tmp_path, mock_gemini_client):
        """Test batch image processing."""
        agent = ImageAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Create second image
        img2 = tmp_path / "damage2.jpg"
        img2.write_bytes(Path(sample_damage_photo).read_bytes())
        
        # Mock responses for both images
        mock_response = MagicMock()
        mock_response.text = '{"damage_type": "collision", "affected_parts": ["bumper"], "severity": "moderate", "estimated_cost": 2000.0, "confidence": 0.9, "valid": true}'
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        images = [
            {"file_path": sample_damage_photo},
            {"file_path": str(img2)}
        ]
        
        result = await agent.analyze("claim-123", images)
        
        assert result["valid"] is True
        assert len(result.get("individual_results", [])) == 2
    
    @pytest.mark.asyncio
    async def test_analyze_aggregates_damage_assessments(self, sample_damage_photo, tmp_path, mock_gemini_client):
        """Verify aggregation logic for multiple images."""
        agent = ImageAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Create multiple images
        img2 = tmp_path / "damage2.jpg"
        img2.write_bytes(Path(sample_damage_photo).read_bytes())
        
        # Mock responses for both images
        mock_response = MagicMock()
        mock_response.text = '{"damage_type": "collision", "affected_parts": ["bumper"], "severity": "moderate", "estimated_cost": 2000.0, "confidence": 0.9, "valid": true}'
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        images = [
            {"file_path": sample_damage_photo},
            {"file_path": str(img2)}
        ]
        
        result = await agent.analyze("claim-123", images)
        
        assert "damage_assessment" in result
        assert result["damage_assessment"].get("image_count") == 2
    
    @pytest.mark.asyncio
    async def test_analyze_detects_tampering(self, sample_damage_photo, mock_gemini_client):
        """Test authenticity detection."""
        agent = ImageAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Test authentic image
        mock_response = MagicMock()
        mock_response.text = '{"damage_type": "collision", "affected_parts": ["bumper"], "severity": "moderate", "estimated_cost": 2000.0, "confidence": 0.9, "valid": true, "notes": "Image appears authentic"}'
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        images = [{"file_path": sample_damage_photo}]
        result = await agent.analyze("claim-123", images)
        
        assert result["valid"] is True
        
        # Test tampered image
        mock_response.text = '{"damage_type": "collision", "affected_parts": ["bumper"], "severity": "moderate", "estimated_cost": 2000.0, "confidence": 0.5, "valid": false, "notes": "Signs of tampering detected"}'
        result = await agent.analyze("claim-123", images)
        assert result["valid"] is False
    
    @pytest.mark.asyncio
    async def test_analyze_with_invalid_image(self, tmp_path):
        """Test handling of corrupted images."""
        agent = ImageAgent()
        agent.client = None
        
        # Create invalid image file
        invalid_img = tmp_path / "corrupted.jpg"
        invalid_img.write_bytes(b"not a valid image")
        
        images = [{"file_path": str(invalid_img)}]
        
        result = await agent.analyze("claim-123", images)
        
        # Should handle gracefully
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_analyze_api_error_handling(self, sample_damage_photo, mock_gemini_client):
        """Test API failure scenarios."""
        agent = ImageAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Simulate API error
        mock_gemini_client.generate_content_async = AsyncMock(side_effect=Exception("API Error"))
        
        images = [{"file_path": sample_damage_photo}]
        
        result = await agent.analyze("claim-123", images)
        
        # Should handle error gracefully
        assert result["valid"] is False or "error" in str(result)
    
    @pytest.mark.asyncio
    async def test_analyze_mock_analysis_fallback(self, sample_damage_photo):
        """Verify mock analysis when API unavailable."""
        agent = ImageAgent()
        agent.client = None
        
        images = [{"file_path": sample_damage_photo}]
        
        result = await agent.analyze("claim-123", images)
        
        assert result["valid"] is True
        assert result["confidence"] == 0.89
        assert "damage_assessment" in result
        assert result["damage_assessment"]["damage_type"] == "collision"
        assert "mock" in result["analysis_id"].lower()
    
    @pytest.mark.asyncio
    @pytest.mark.real_api
    async def test_analyze_with_valid_damage_photo_real_api(self, sample_damage_photo, real_gemini_client):
        """Test damage photo analysis with real Gemini API."""
        if not real_gemini_client:
            pytest.skip("Real Gemini API not available")
        
        agent = ImageAgent(api_key=os.getenv("GOOGLE_AI_API_KEY"))
        agent.client = real_gemini_client
        
        images = [{"file_path": sample_damage_photo}]
        
        result = await agent.analyze("claim-123", images)
        
        assert result is not None
        assert "summary" in result
        assert "confidence" in result
        assert "damage_assessment" in result
    
    @pytest.mark.asyncio
    async def test_analyze_handles_fire_damage(self, sample_fire_damage_photo):
        """Test fire damage detection."""
        agent = ImageAgent()
        agent.client = None  # Use mock
        
        images = [{"file_path": sample_fire_damage_photo}]
        
        result = await agent.analyze("claim-123", images)
        
        assert result["valid"] is True
        assert "damage_assessment" in result
    
    @pytest.mark.asyncio
    async def test_analyze_handles_water_damage(self, sample_water_damage_photo):
        """Test water damage detection."""
        agent = ImageAgent()
        agent.client = None  # Use mock
        
        images = [{"file_path": sample_water_damage_photo}]
        
        result = await agent.analyze("claim-123", images)
        
        assert result["valid"] is True
        assert "damage_assessment" in result
    
    @pytest.mark.asyncio
    async def test_analyze_handles_malformed_json_response(self, sample_damage_photo, mock_gemini_client):
        """Test handling of malformed JSON from API."""
        agent = ImageAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Return non-JSON text
        mock_response = MagicMock()
        mock_response.text = "The image shows significant damage to the front bumper area."
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        images = [{"file_path": sample_damage_photo}]
        
        result = await agent.analyze("claim-123", images)
        
        # Should fallback to text parsing
        assert result is not None
        assert "valid" in result
        assert "damage_assessment" in result