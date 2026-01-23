"""
Tests for GatewayService. get_balance is supported.
create_micropayment and validate_receipt are deprecated (x402; evaluations are free).
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal
from src.services.gateway import GatewayService


@pytest.mark.asyncio
async def test_create_micropayment_deprecated():
    """create_micropayment raises NotImplementedError (x402 deprecated)."""
    service = GatewayService(api_key=None)
    with pytest.raises(NotImplementedError, match="x402 deprecated"):
        await service.create_micropayment(
            amount=Decimal("0.10"),
            payment_id="test-payment-123",
            metadata={"claim_id": "test-claim"},
        )


@pytest.mark.asyncio
async def test_validate_receipt_deprecated():
    """validate_receipt raises NotImplementedError (x402 deprecated)."""
    service = GatewayService(api_key=None)
    with pytest.raises(NotImplementedError, match="x402 deprecated"):
        await service.validate_receipt("any_receipt_token")


@pytest.mark.asyncio
async def test_get_balance_no_api_key():
    """get_balance without API key returns None."""
    service = GatewayService(api_key=None)
    balance = await service.get_balance()
    assert balance is None


@pytest.mark.asyncio
async def test_get_balance_no_address():
    """get_balance without address returns None."""
    service = GatewayService(api_key="test_key", agent_wallet_address=None)
    balance = await service.get_balance()
    assert balance is None
