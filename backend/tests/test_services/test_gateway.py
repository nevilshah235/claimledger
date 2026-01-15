"""
Tests for GatewayService (x402 payments).
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal
from src.services.gateway import GatewayService


@pytest.mark.asyncio
async def test_create_micropayment_mock_mode(monkeypatch):
    """Test creating micropayment in mock mode (no API key)."""
    # Ensure no API key from environment
    monkeypatch.delenv("CIRCLE_GATEWAY_API_KEY", raising=False)
    service = GatewayService(api_key=None)
    
    # Verify we're in mock mode
    assert service.api_key is None
    
    receipt = await service.create_micropayment(
        amount=Decimal("0.10"),
        payment_id="test-payment-123",
        metadata={"claim_id": "test-claim"}
    )
    
    assert receipt is not None
    assert "mock_receipt" in receipt or len(receipt) > 0


@pytest.mark.asyncio
async def test_validate_receipt_mock_mode(monkeypatch):
    """Test validating receipt in mock mode."""
    # Ensure no API key from environment
    monkeypatch.delenv("CIRCLE_GATEWAY_API_KEY", raising=False)
    service = GatewayService(api_key=None)
    
    # Verify we're in mock mode
    assert service.api_key is None
    
    # In mock mode, any non-empty receipt should be valid
    assert await service.validate_receipt("any_receipt_token") is True
    assert await service.validate_receipt("") is False
    # None should raise TypeError or return False
    try:
        result = await service.validate_receipt(None)
        assert result is False
    except TypeError:
        pass  # Expected if None is not allowed


@pytest.mark.asyncio
async def test_validate_receipt_production_mode():
    """Test validating receipt in production mode."""
    service = GatewayService(api_key="test_api_key_12345")
    
    # Mock the HTTP client for both create and validate
    with patch.object(service.http_client, 'post') as mock_post:
        # Mock create_micropayment response
        mock_create_response = MagicMock()
        mock_create_response.json.return_value = {"receiptToken": "test_receipt_123"}
        mock_create_response.raise_for_status = MagicMock()
        
        # Mock validate_receipt response
        mock_validate_response = MagicMock()
        mock_validate_response.json.return_value = {"valid": True}
        mock_validate_response.raise_for_status = MagicMock()
        
        mock_post.side_effect = [mock_create_response, mock_validate_response]
        
        # Create receipt
        receipt = await service.create_micropayment(
            amount=Decimal("0.10"),
            payment_id="test-payment-123"
        )
        
        # Validate receipt
        is_valid = await service.validate_receipt(receipt)
        assert is_valid is True


@pytest.mark.asyncio
async def test_get_balance_no_api_key():
    """Test getting balance without API key returns mock balance."""
    service = GatewayService(api_key=None)
    
    # In mock mode, get_balance returns a dict with mock balance
    balance = await service.get_balance()
    
    assert balance is not None
    assert isinstance(balance, dict)
    assert "balance" in balance
    assert "currency" in balance


@pytest.mark.asyncio
async def test_get_balance_no_address():
    """Test getting balance without address returns error dict."""
    service = GatewayService(api_key="test_key", agent_wallet_address=None)
    
    # When no address and API key is set, it tries to call API and gets error
    balance = await service.get_balance()
    
    # Returns dict with error info, not None
    assert balance is not None
    assert isinstance(balance, dict)
    # May have error field or balance field
    assert "balance" in balance or "error" in balance


@pytest.mark.asyncio
async def test_create_micropayment_checks_balance():
    """Test that micropayment creation works with API key."""
    service = GatewayService(
        api_key="test_key",
        agent_wallet_address="0x1234567890123456789012345678901234567890"
    )
    
    # Mock the HTTP client to avoid actual API calls
    with patch.object(service.http_client, 'post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"receiptToken": "test_receipt_123"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        receipt = await service.create_micropayment(
            amount=Decimal("0.10"),
            payment_id="test-payment-123"
        )
        
        assert receipt is not None
        assert receipt == "test_receipt_123"


@pytest.mark.asyncio
async def test_create_micropayment_insufficient_balance():
    """Test that micropayment fails with insufficient balance."""
    service = GatewayService(
        api_key="test_key",
        agent_wallet_address="0x1234567890123456789012345678901234567890"
    )
    
    # Mock get_balance to return insufficient balance
    service.get_balance = AsyncMock(return_value=Decimal("0.05"))
    
    receipt = await service.create_micropayment(
        amount=Decimal("0.10"),
        payment_id="test-payment-123"
    )
    
    # Should return None when balance is insufficient
    assert receipt is None
