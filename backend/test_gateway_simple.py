#!/usr/bin/env python3
"""Simple test for GatewayService without full backend."""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from services.gateway import GatewayService

async def test_mock_mode():
    """Test GatewayService in mock mode."""
    print("Testing GatewayService in mock mode...")
    
    gateway = GatewayService()
    
    # Test create_micropayment
    receipt = await gateway.create_micropayment(
        amount=Decimal("0.10"),
        payment_id="test-123",
        metadata={"test": "true"}
    )
    
    print(f"✅ Created mock receipt: {receipt}")
    
    # Test validate_receipt
    is_valid = await gateway.validate_receipt(receipt)
    print(f"✅ Receipt validation: {is_valid}")
    
    # Test with API key (if set)
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("CIRCLE_GATEWAY_API_KEY")
    if api_key:
        print(f"\nTesting with real API key (length: {len(api_key)})...")
        gateway_real = GatewayService()
        
        # Try to create a real payment
        receipt_real = await gateway_real.create_micropayment(
            amount=Decimal("0.10"),
            payment_id="test-real-123",
            metadata={"test": "true"}
        )
        
        if receipt_real:
            print(f"✅ Created real receipt: {receipt_real[:50]}...")
            
            # Validate it
            is_valid_real = await gateway_real.validate_receipt(receipt_real)
            print(f"✅ Real receipt validation: {is_valid_real}")
        else:
            print("⚠️  Real payment creation failed (check API key and agent wallet)")
    else:
        print("\n⚠️  No CIRCLE_GATEWAY_API_KEY set, skipping real API test")
    
    await gateway.close()
    if api_key:
        await gateway_real.close()

if __name__ == "__main__":
    asyncio.run(test_mock_mode())
