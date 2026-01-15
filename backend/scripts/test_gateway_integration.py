#!/usr/bin/env python3
"""
Test Circle Gateway x402 Integration End-to-End.

Tests the complete flow:
1. Call verifier endpoint (should return 402)
2. Create payment via Gateway
3. Retry with receipt (should succeed)
"""

import os
import sys
import asyncio
import httpx
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = "http://localhost:8000"
GATEWAY_API_KEY = os.getenv("CIRCLE_GATEWAY_API_KEY")
AGENT_WALLET = os.getenv("AGENT_WALLET_ADDRESS")


async def test_verifier_endpoint_without_receipt():
    """Test that verifier returns 402 without receipt."""
    print("\n🧪 Test 1: Verifier endpoint without receipt (should return 402)")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/verifier/document",
            json={
                "claim_id": "test-claim-123",
                "document_path": "test/invoice.pdf"
            }
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 402:
            print("   ✅ Correctly returned 402 Payment Required")
            data = response.json()
            print(f"   Amount: {data.get('amount')} {data.get('currency')}")
            print(f"   Payment ID: {data.get('gateway_payment_id')}")
            return data.get("gateway_payment_id")
        else:
            print(f"   ❌ Expected 402, got {response.status_code}")
            print(f"   Response: {response.text}")
            return None


async def test_gateway_service():
    """Test GatewayService directly."""
    print("\n🧪 Test 2: GatewayService.create_micropayment()")
    
    from src.services.gateway import GatewayService
    
    gateway = GatewayService()
    
    payment_id = "test-payment-123"
    amount = Decimal("0.10")
    
    print(f"   Creating payment: ${amount} USDC")
    print(f"   Payment ID: {payment_id}")
    print(f"   Agent Wallet: {AGENT_WALLET or 'NOT SET'}")
    
    receipt = await gateway.create_micropayment(
        amount=amount,
        payment_id=payment_id,
        metadata={"test": "true"}
    )
    
    if receipt:
        print(f"   ✅ Payment created, receipt: {receipt[:50]}...")
        return receipt
    else:
        print("   ❌ Payment creation failed")
        return None


async def test_verifier_with_receipt(receipt: str):
    """Test verifier endpoint with receipt."""
    print("\n🧪 Test 3: Verifier endpoint with receipt (should succeed)")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/verifier/document",
            json={
                "claim_id": "test-claim-123",
                "document_path": "test/invoice.pdf"
            },
            headers={
                "X-Payment-Receipt": receipt
            }
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Verification succeeded with receipt")
            data = response.json()
            print(f"   Valid: {data.get('valid')}")
            print(f"   Verification ID: {data.get('verification_id')}")
            return True
        else:
            print(f"   ❌ Expected 200, got {response.status_code}")
            print(f"   Response: {response.text}")
            return False


async def test_x402_client_flow():
    """Test complete x402 client flow."""
    print("\n🧪 Test 4: X402Client complete flow")
    
    from src.services.x402_client import X402Client
    
    x402_client = X402Client(base_url=API_BASE_URL)
    
    try:
        result = await x402_client.verify_document(
            claim_id="test-claim-456",
            document_path="test/invoice.pdf"
        )
        
        if result and result.get("valid"):
            print("   ✅ X402Client flow succeeded")
            print(f"   Result: {result}")
            return True
        else:
            print(f"   ❌ X402Client flow failed: {result}")
            return False
    except Exception as e:
        print(f"   ❌ X402Client flow error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await x402_client.close()


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Circle Gateway x402 Integration Test")
    print("=" * 60)
    
    print(f"\n📋 Configuration:")
    print(f"   API URL: {API_BASE_URL}")
    print(f"   Gateway API Key: {'SET' if GATEWAY_API_KEY else 'NOT SET'}")
    print(f"   Agent Wallet: {AGENT_WALLET or 'NOT SET'}")
    
    if not GATEWAY_API_KEY:
        print("\n⚠️  Warning: CIRCLE_GATEWAY_API_KEY not set, will use mock mode")
    
    # Check if backend is running
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_BASE_URL}/health")
            if response.status_code != 200:
                print(f"\n❌ Backend not healthy: {response.status_code}")
                return
    except httpx.RequestError:
        print(f"\n❌ Backend not running at {API_BASE_URL}")
        print("   Start backend: cd backend && rye run uvicorn src.main:app --reload")
        return
    
    print("   ✅ Backend is running")
    
    # Run tests
    results = []
    
    # Test 1: 402 response
    payment_id = await test_verifier_endpoint_without_receipt()
    results.append(("402 Response", payment_id is not None))
    
    # Test 2: Gateway service
    receipt = await test_gateway_service()
    results.append(("Gateway Payment", receipt is not None))
    
    # Test 3: Verifier with receipt
    if receipt:
        success = await test_verifier_with_receipt(receipt)
        results.append(("Verifier with Receipt", success))
    
    # Test 4: Complete x402 flow
    x402_success = await test_x402_client_flow()
    results.append(("X402Client Flow", x402_success))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check logs above.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
