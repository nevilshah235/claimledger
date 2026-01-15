"""
Tests for X402Client (automatic x402 payment handling).
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.x402_client import X402Client, X402PaymentError
from src.services.gateway import GatewayService


@pytest.mark.asyncio
async def test_call_with_payment_no_402():
    """Test calling endpoint that doesn't require payment."""
    mock_gateway = AsyncMock(spec=GatewayService)
    client = X402Client(gateway_service=mock_gateway, base_url="http://localhost:8000")
    
    # Mock HTTP client to return success
    with patch.object(client.http_client, 'request') as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_request.return_value = mock_response
        
        result = await client.call_with_payment(
            url="/test/endpoint",
            data={"test": "data"},
            claim_id="test-claim-id"
        )
        
        assert result == {"result": "success"}
        # Should not call gateway
        mock_gateway.create_micropayment.assert_not_called()


@pytest.mark.asyncio
async def test_call_with_payment_402_flow():
    """Test automatic payment handling when 402 is returned."""
    mock_gateway = AsyncMock(spec=GatewayService)
    mock_gateway.create_micropayment = AsyncMock(return_value="receipt_token_12345")
    client = X402Client(gateway_service=mock_gateway, base_url="http://localhost:8000")
    
    # Mock HTTP client to return 402 first, then success
    with patch.object(client.http_client, 'request') as mock_request:
        # First call: 402 Payment Required
        mock_402_response = MagicMock()
        mock_402_response.status_code = 402
        mock_402_response.json.return_value = {
            "error": "Payment required",
            "amount": "0.10",
            "gateway_payment_id": "payment-123"
        }
        mock_402_response.headers = {"X-Payment-Amount": "0.10", "X-Payment-Description": "Test payment"}
        
        # Second call: Success after payment
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {"result": "success"}
        
        mock_request.side_effect = [mock_402_response, mock_success_response]
        
        result = await client.call_with_payment(
            url="/test/endpoint",
            data={"test": "data"},
            claim_id="test-claim-id"
        )
        
        assert result == {"result": "success"}
        # Should have called gateway to create payment
        mock_gateway.create_micropayment.assert_called_once()
        # Should have retried with receipt
        assert mock_request.call_count == 2
        # Check receipt was in headers
        second_call = mock_request.call_args_list[1]
        assert "X-Payment-Receipt" in second_call[1]["headers"]


@pytest.mark.asyncio
async def test_verify_document():
    """Test verify_document convenience method."""
    mock_gateway = AsyncMock(spec=GatewayService)
    mock_gateway.create_micropayment = AsyncMock(return_value="receipt_token")
    client = X402Client(gateway_service=mock_gateway, base_url="http://localhost:8000")
    
    with patch.object(client.http_client, 'request') as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "extracted_data": {"amount": 1000.0},
            "valid": True,
            "verification_id": "test-id"
        }
        mock_request.return_value = mock_response
        
        result = await client.verify_document("test-claim-id", "/path/to/doc.pdf")
        
        assert result["valid"] is True
        assert "extracted_data" in result


@pytest.mark.asyncio
async def test_verify_image():
    """Test verify_image convenience method."""
    mock_gateway = AsyncMock(spec=GatewayService)
    mock_gateway.create_micropayment = AsyncMock(return_value="receipt_token")
    client = X402Client(gateway_service=mock_gateway, base_url="http://localhost:8000")
    
    with patch.object(client.http_client, 'request') as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "damage_assessment": {"severity": "moderate"},
            "valid": True,
            "analysis_id": "test-id"
        }
        mock_request.return_value = mock_response
        
        result = await client.verify_image("test-claim-id", "/path/to/image.jpg")
        
        assert result["valid"] is True
        assert "damage_assessment" in result


@pytest.mark.asyncio
async def test_verify_fraud():
    """Test verify_fraud convenience method."""
    mock_gateway = AsyncMock(spec=GatewayService)
    mock_gateway.create_micropayment = AsyncMock(return_value="receipt_token")
    client = X402Client(gateway_service=mock_gateway, base_url="http://localhost:8000")
    
    with patch.object(client.http_client, 'request') as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "fraud_score": 0.05,
            "risk_level": "LOW",
            "check_id": "test-id"
        }
        mock_request.return_value = mock_response
        
        result = await client.verify_fraud("test-claim-id")
        
        assert result["risk_level"] == "LOW"
        assert "fraud_score" in result


@pytest.mark.asyncio
async def test_payment_error_on_failure():
    """Test that X402PaymentError is raised when payment fails."""
    mock_gateway = AsyncMock(spec=GatewayService)
    mock_gateway.create_micropayment = AsyncMock(return_value=None)  # Payment fails
    client = X402Client(gateway_service=mock_gateway, base_url="http://localhost:8000")
    
    with patch.object(client.http_client, 'request') as mock_request:
        mock_402_response = MagicMock()
        mock_402_response.status_code = 402
        mock_402_response.json.return_value = {
            "error": "Payment required",
            "amount": "0.10",
            "gateway_payment_id": "payment-123"
        }
        mock_402_response.headers = {"X-Payment-Amount": "0.10"}
        mock_request.return_value = mock_402_response
        
        with pytest.raises(X402PaymentError):
            await client.call_with_payment(
                url="/test/endpoint",
                data={"test": "data"},
                claim_id="test-claim-id"
            )
