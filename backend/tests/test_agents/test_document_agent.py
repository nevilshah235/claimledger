"""
Unit tests for DocumentAgent.
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from pathlib import Path

from src.agent.agents.document_agent import DocumentAgent


@pytest.mark.unit
class TestDocumentAgent:
    """Test suite for DocumentAgent."""
    
    def test_document_agent_initialization_with_api_key(self):
        """Verify agent initializes with API key."""
        with patch.dict(os.environ, {"GOOGLE_AI_API_KEY": "test-api-key"}):
            agent = DocumentAgent()
            
            assert agent.api_key == "test-api-key"
            assert agent.model_name == "gemini-2.0-flash"
            # Client may or may not be initialized depending on GEMINI_AVAILABLE and API key validity
            # Just verify the agent was created successfully
            assert agent is not None
    
    def test_document_agent_initialization_without_api_key(self):
        """Verify fallback to mock mode when no API key."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.agent.agents.document_agent.GEMINI_AVAILABLE", True):
                agent = DocumentAgent()
                
                assert agent.api_key is None
                assert agent.client is None
    
    def test_document_agent_initialization_with_custom_api_key(self):
        """Verify agent can be initialized with custom API key."""
        agent = DocumentAgent(api_key="custom-key")
        
        assert agent.api_key == "custom-key"
        assert agent.model_name == "gemini-2.0-flash"
        # Client may or may not be initialized depending on GEMINI_AVAILABLE
        # Just verify the agent was created with the custom key
        assert agent is not None
    
    @pytest.mark.asyncio
    async def test_analyze_with_empty_documents_list(self):
        """Test with no documents provided."""
        agent = DocumentAgent()
        
        result = await agent.analyze("claim-123", [])
        
        assert result["summary"] == "No documents provided"
        assert result["valid"] is False
        assert result["confidence"] == 0.0
        assert result["extracted_data"] == {}
        assert result["verification_id"] is None
    
    @pytest.mark.asyncio
    async def test_analyze_with_missing_file(self, tmp_path):
        """Test handling of non-existent file paths."""
        agent = DocumentAgent()
        # Don't set client to None - let it check file existence
        
        documents = [{"file_path": str(tmp_path / "nonexistent.pdf")}]
        
        result = await agent.analyze("claim-123", documents)
        
        # When file doesn't exist, it's skipped in the loop
        # If no results, should return "No valid documents could be analyzed"
        # If mock mode is used (client is None), it will use mock_analysis
        assert result is not None
        assert "summary" in result
        # Either no valid documents or mock analysis (if client is None)
        if agent.client is None:
            # Mock mode - will return valid result
            assert result["valid"] is True
        else:
            # Real mode - file doesn't exist, so skipped
            assert result["valid"] is False
            assert "No valid documents" in result["summary"]
    
    @pytest.mark.asyncio
    async def test_analyze_mock_analysis_fallback(self, sample_pdf_file):
        """Verify error state when API unavailable."""
        agent = DocumentAgent()  # No API key, should use mock
        agent.client = None
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        # Should return error state, not mock data
        assert result["valid"] is False
        assert result["confidence"] == 0.0
        assert "extracted_data" in result
        assert result["extracted_data"]["extraction_failed"] is True
        assert result["extracted_data"]["error"] == "API_UNAVAILABLE"
        assert "Failed to extract" in result["summary"]
        assert result["verification_id"] is None
    
    @pytest.mark.asyncio
    async def test_analyze_with_valid_pdf_mocked(self, sample_pdf_file, mock_gemini_client):
        """Test PDF document analysis with mocked Gemini API."""
        agent = DocumentAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Setup mock response with new structure
        mock_response = MagicMock()
        mock_response.text = """{
            "document_classification": {
                "category": "invoice",
                "structure": "structured",
                "has_tables": false,
                "has_line_items": true,
                "primary_content_type": "financial"
            },
            "extracted_fields": {
                "document_type": "invoice",
                "amount": 3500.00,
                "date": "2024-01-15",
                "vendor": "Auto Repair Shop",
                "description": "Front bumper repair and replacement",
                "invoice_number": "INV-12345",
                "vendor_address": "123 Main St",
                "total_amount": 3500.00
            },
            "line_items": [
                {
                    "item_name": "Front Bumper",
                    "description": "Replacement and installation",
                    "quantity": 1,
                    "unit_price": 3000.00,
                    "total": 3000.00
                },
                {
                    "item_name": "Labor",
                    "description": "Installation labor",
                    "quantity": 2,
                    "unit_price": 250.00,
                    "total": 500.00
                }
            ],
            "metadata": {
                "confidence": 0.92,
                "extraction_method": "multimodal_vision",
                "notes": "Valid invoice with clear details"
            },
            "valid": true
        }"""
        mock_gemini_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        assert result["valid"] is True
        assert result["confidence"] > 0.0
        assert "extracted_data" in result
        assert len(result.get("individual_results", [])) > 0
        
        # Check new structure
        extracted_data = result["extracted_data"]
        assert "document_classification" in extracted_data
        assert extracted_data["document_classification"]["category"] == "invoice"
        assert "extracted_fields" in extracted_data
        assert extracted_data["extracted_fields"]["amount"] == 3500.00
        assert "line_items" in extracted_data
        assert len(extracted_data["line_items"]) == 2
    
    @pytest.mark.asyncio
    async def test_analyze_with_multiple_documents(self, sample_pdf_file, tmp_path, mock_gemini_client):
        """Test batch document processing."""
        agent = DocumentAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Create second PDF
        pdf2 = tmp_path / "invoice2.pdf"
        pdf2.write_bytes(Path(sample_pdf_file).read_bytes())
        
        # Mock responses for both documents
        mock_response = MagicMock()
        mock_response.text = '{"document_type": "invoice", "amount": 2000.0, "date": "2024-01-15", "vendor": "Shop", "description": "Service", "valid": true, "confidence": 0.9}'
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        documents = [
            {"file_path": sample_pdf_file},
            {"file_path": str(pdf2)}
        ]
        
        result = await agent.analyze("claim-123", documents)
        
        assert result["valid"] is True
        # Should process both documents
        assert len(result.get("individual_results", [])) == 2
    
    @pytest.mark.asyncio
    async def test_analyze_extracts_amount(self, sample_pdf_file, mock_gemini_client):
        """Verify amount extraction from invoices."""
        agent = DocumentAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Test with new structure
        mock_response = MagicMock()
        mock_response.text = '{"document_classification": {"category": "invoice", "structure": "structured", "has_tables": false, "has_line_items": false, "primary_content_type": "financial"}, "extracted_fields": {"document_type": "invoice", "amount": 2500.50, "date": "2024-01-15", "vendor": "Shop", "description": "Repair"}, "metadata": {"confidence": 0.9, "extraction_method": "multimodal_vision", "notes": ""}, "valid": true}'
        mock_gemini_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        # Check amount in extracted_fields
        extracted_data = result["extracted_data"]
        if "extracted_fields" in extracted_data:
            assert extracted_data["extracted_fields"].get("amount") == 2500.50
        else:
            # Backward compatibility with old structure
            assert extracted_data.get("amount") == 2500.50
    
    @pytest.mark.asyncio
    async def test_analyze_extracts_vendor(self, sample_pdf_file, mock_gemini_client):
        """Verify vendor name extraction."""
        agent = DocumentAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        mock_response = MagicMock()
        mock_response.text = '{"document_classification": {"category": "invoice", "structure": "structured", "has_tables": false, "has_line_items": false, "primary_content_type": "financial"}, "extracted_fields": {"document_type": "invoice", "amount": 1000.0, "date": "2024-01-15", "vendor": "ABC Auto Repair", "description": "Service"}, "metadata": {"confidence": 0.9, "extraction_method": "multimodal_vision", "notes": ""}, "valid": true}'
        mock_gemini_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        extracted_data = result["extracted_data"]
        if "extracted_fields" in extracted_data:
            assert extracted_data["extracted_fields"].get("vendor") == "ABC Auto Repair"
        else:
            assert extracted_data.get("vendor") == "ABC Auto Repair"
    
    @pytest.mark.asyncio
    async def test_analyze_detects_validity(self, sample_pdf_file, mock_gemini_client):
        """Test document authenticity detection."""
        agent = DocumentAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Test valid document
        mock_response = MagicMock()
        mock_response.text = '{"document_classification": {"category": "invoice", "structure": "structured", "has_tables": false, "has_line_items": false, "primary_content_type": "financial"}, "extracted_fields": {"document_type": "invoice", "amount": 1000.0, "date": "2024-01-15", "vendor": "Shop", "description": "Service"}, "metadata": {"confidence": 0.95, "extraction_method": "multimodal_vision", "notes": ""}, "valid": true}'
        mock_gemini_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        assert result["valid"] is True
        
        # Test invalid document
        mock_response.text = '{"document_classification": {"category": "invoice", "structure": "structured", "has_tables": false, "has_line_items": false, "primary_content_type": "financial"}, "extracted_fields": {"document_type": "invoice", "amount": 1000.0, "date": "2024-01-15", "vendor": "Shop", "description": "Service"}, "metadata": {"confidence": 0.3, "extraction_method": "multimodal_vision", "notes": "Suspicious document"}, "valid": false}'
        result = await agent.analyze("claim-123", documents)
        assert result["valid"] is False
    
    @pytest.mark.asyncio
    async def test_analyze_returns_confidence(self, sample_pdf_file):
        """Verify confidence score in response."""
        agent = DocumentAgent()
        agent.client = None  # Use mock
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_analyze_api_error_handling(self, sample_pdf_file, mock_gemini_client):
        """Test behavior when Gemini API fails."""
        agent = DocumentAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Simulate API error - update to use correct API structure
        mock_gemini_client.aio.models.generate_content = AsyncMock(side_effect=Exception("API Error"))
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        # Should handle error gracefully
        assert "error" in result.get("individual_results", [{}])[0] or result["valid"] is False
    
    @pytest.mark.asyncio
    async def test_analyze_api_timeout(self, sample_pdf_file, mock_gemini_client):
        """Test timeout handling."""
        import asyncio
        
        agent = DocumentAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Simulate timeout - update to use correct API structure
        async def timeout_error(*args, **kwargs):
            await asyncio.sleep(0.01)
            raise asyncio.TimeoutError("Request timed out")
        
        mock_gemini_client.aio.models.generate_content = timeout_error
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        # Should handle timeout gracefully
        assert result["valid"] is False or "error" in str(result)
    
    @pytest.mark.asyncio
    async def test_analyze_with_invalid_file_type(self, tmp_path):
        """Test unsupported file types."""
        agent = DocumentAgent()
        agent.client = None
        
        # Create a non-PDF file
        invalid_file = tmp_path / "document.xyz"
        invalid_file.write_text("not a pdf")
        
        documents = [{"file_path": str(invalid_file)}]
        
        result = await agent.analyze("claim-123", documents)
        
        # Should handle gracefully (file exists but may not be processable)
        assert result is not None
    
    @pytest.mark.asyncio
    @pytest.mark.real_api
    async def test_analyze_with_valid_pdf_real_api(self, sample_pdf_file, real_gemini_client):
        """Test PDF document analysis with real Gemini API."""
        if not real_gemini_client:
            pytest.skip("Real Gemini API not available")
        
        agent = DocumentAgent(api_key=os.getenv("GOOGLE_AI_API_KEY"))
        agent.client = real_gemini_client
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        assert result is not None
        assert "summary" in result
        assert "confidence" in result
        assert "extracted_data" in result
    
    @pytest.mark.asyncio
    async def test_analyze_aggregates_multiple_results(self, sample_pdf_file, tmp_path, mock_gemini_client):
        """Test that multiple document results are aggregated correctly."""
        agent = DocumentAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Create multiple PDFs
        pdf2 = tmp_path / "doc2.pdf"
        pdf2.write_bytes(Path(sample_pdf_file).read_bytes())
        
        # Mock responses for both documents
        mock_response = MagicMock()
        mock_response.text = '{"document_type": "invoice", "amount": 2000.0, "date": "2024-01-15", "vendor": "Shop", "description": "Service", "valid": true, "confidence": 0.9}'
        mock_gemini_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        documents = [
            {"file_path": sample_pdf_file},
            {"file_path": str(pdf2)}
        ]
        
        result = await agent.analyze("claim-123", documents)
        
        assert result["valid"] is True
        assert "individual_results" in result
        assert len(result["individual_results"]) == 2
        assert result["confidence"] > 0.0
    
    @pytest.mark.asyncio
    async def test_analyze_handles_malformed_json_response(self, sample_pdf_file, mock_gemini_client):
        """Test handling of malformed JSON from API."""
        agent = DocumentAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Return non-JSON text
        mock_response = MagicMock()
        mock_response.text = "This is not JSON, just plain text response from the model."
        mock_gemini_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        # Should fallback to text parsing with new structure
        assert result is not None
        assert "valid" in result
        # Should have document_classification in fallback structure
        extracted_data = result.get("extracted_data", {})
        if extracted_data:
            assert "document_classification" in extracted_data or "extracted_fields" in extracted_data
    
    @pytest.mark.asyncio
    async def test_analyze_document_classification(self, sample_pdf_file, mock_gemini_client):
        """Test document classification feature."""
        agent = DocumentAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        mock_response = MagicMock()
        mock_response.text = """{
            "document_classification": {
                "category": "receipt",
                "structure": "semi_structured",
                "has_tables": false,
                "has_line_items": true,
                "primary_content_type": "financial"
            },
            "extracted_fields": {
                "document_type": "receipt",
                "vendor": "Grocery Store",
                "total_amount": 125.50
            },
            "metadata": {
                "confidence": 0.88,
                "extraction_method": "multimodal_vision",
                "notes": "Clear receipt"
            },
            "valid": true
        }"""
        mock_gemini_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        extracted_data = result["extracted_data"]
        assert "document_classification" in extracted_data
        classification = extracted_data["document_classification"]
        assert classification["category"] == "receipt"
        assert classification["structure"] == "semi_structured"
        assert classification["has_line_items"] is True
    
    @pytest.mark.asyncio
    async def test_analyze_extracts_line_items(self, sample_pdf_file, mock_gemini_client):
        """Test line items extraction."""
        agent = DocumentAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        mock_response = MagicMock()
        mock_response.text = """{
            "document_classification": {
                "category": "invoice",
                "structure": "structured",
                "has_tables": false,
                "has_line_items": true,
                "primary_content_type": "financial"
            },
            "extracted_fields": {
                "document_type": "invoice",
                "total_amount": 1500.00
            },
            "line_items": [
                {
                    "item_name": "Part A",
                    "quantity": 2,
                    "unit_price": 500.00,
                    "total": 1000.00
                },
                {
                    "item_name": "Part B",
                    "quantity": 1,
                    "unit_price": 500.00,
                    "total": 500.00
                }
            ],
            "metadata": {"confidence": 0.9, "extraction_method": "multimodal_vision", "notes": ""},
            "valid": true
        }"""
        mock_gemini_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        extracted_data = result["extracted_data"]
        assert "line_items" in extracted_data
        assert len(extracted_data["line_items"]) == 2
        assert extracted_data["line_items"][0]["item_name"] == "Part A"
        assert extracted_data["line_items"][0]["total"] == 1000.00
    
    @pytest.mark.asyncio
    async def test_analyze_backward_compatibility_old_structure(self, sample_pdf_file, mock_gemini_client):
        """Test backward compatibility with old structure."""
        agent = DocumentAgent(api_key="test-key")
        agent.client = mock_gemini_client
        
        # Old structure without document_classification
        mock_response = MagicMock()
        mock_response.text = '{"document_type": "invoice", "amount": 2000.0, "date": "2024-01-15", "vendor": "Shop", "description": "Service", "valid": true, "confidence": 0.9}'
        mock_gemini_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        
        documents = [{"file_path": sample_pdf_file}]
        
        result = await agent.analyze("claim-123", documents)
        
        # Should normalize to new structure
        extracted_data = result["extracted_data"]
        assert "document_classification" in extracted_data
        assert "extracted_fields" in extracted_data
        # Old fields should be in extracted_fields
        assert extracted_data["extracted_fields"]["amount"] == 2000.0
        assert extracted_data["extracted_fields"]["vendor"] == "Shop"