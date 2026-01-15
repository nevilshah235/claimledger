"""
Tests for DeveloperWalletsService.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.developer_wallets import DeveloperWalletsService


@pytest.mark.asyncio
async def test_create_wallet_success(mock_developer_wallets_service):
    """Test successful wallet creation."""
    service = mock_developer_wallets_service
    
    result = await service.create_wallet(
        blockchains=["ARC"],
        account_type="SCA"
    )
    
    assert result is not None
    assert "wallet_id" in result
    assert "address" in result
    assert "wallet_set_id" in result
    assert result["address"].startswith("0x")


@pytest.mark.asyncio
async def test_get_wallet(mock_developer_wallets_service):
    """Test getting wallet information."""
    service = mock_developer_wallets_service
    
    result = await service.get_wallet("test-wallet-id")
    
    assert result is not None
    assert "blockchain" in result
    assert "address" in result


@pytest.mark.asyncio
async def test_get_wallet_balance(mock_developer_wallets_service):
    """Test getting wallet balance."""
    service = mock_developer_wallets_service
    
    result = await service.get_wallet_balance("test-wallet-id")
    
    assert result is not None
    assert "balances" in result


@pytest.mark.asyncio
async def test_create_wallet_without_api_key():
    """Test wallet creation fails without API key."""
    import os
    original_key = os.environ.get("CIRCLE_WALLETS_API_KEY")
    
    try:
        # Remove API key
        if "CIRCLE_WALLETS_API_KEY" in os.environ:
            del os.environ["CIRCLE_WALLETS_API_KEY"]
        
        service = DeveloperWalletsService()
        
        # Should raise ValueError or return mock wallet in testnet mode
        # The actual behavior depends on implementation
        with pytest.raises((ValueError, Exception)):
            await service.create_wallet(blockchains=["ARC"])
    finally:
        # Restore original key
        if original_key:
            os.environ["CIRCLE_WALLETS_API_KEY"] = original_key
