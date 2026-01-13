#!/usr/bin/env python3
"""Get testnet USDC on Arc using Circle Gateway."""

import os
import sys
import httpx
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

load_dotenv()

GATEWAY_API_KEY = os.getenv("CIRCLE_GATEWAY_API_KEY")
GATEWAY_API_URL = "https://api.circle.com/v1/gateway"  # Sandbox/testnet


def create_gateway_balance():
    """Create a Gateway balance for cross-chain USDC."""
    
    if not GATEWAY_API_KEY:
        print("❌ Error: CIRCLE_GATEWAY_API_KEY not found in .env")
        print("   Get your API key from: https://developers.circle.com")
        print("   Add to backend/.env: CIRCLE_GATEWAY_API_KEY=your_key_here")
        sys.exit(1)
    
    headers = {
        "Authorization": f"Bearer {GATEWAY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        print("🚀 Creating Gateway balance...")
        response = httpx.post(
            f"{GATEWAY_API_URL}/balances",
            headers=headers,
            json={
                "blockchains": ["ARC", "ETH-SEPOLIA"]  # Arc + Ethereum testnet
            }
        )
        response.raise_for_status()
        
        balance_data = response.json()["data"]
        balance_id = balance_data["balanceId"]
        
        print(f"✅ Created Gateway Balance:")
        print(f"   Balance ID: {balance_id}")
        print(f"   Supported Chains: ARC, ETH-SEPOLIA")
        print(f"\n   📝 Add to backend/.env:")
        print(f"   GATEWAY_BALANCE_ID={balance_id}")
        
        return balance_id
        
    except httpx.HTTPStatusError as e:
        print(f"❌ API Error: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
        print("\n   Check:")
        print("   - API key is correct")
        print("   - You're using Sandbox/testnet key")
        print("   - API key has Gateway permissions")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def get_balance_info(balance_id: str):
    """Get Gateway balance information."""
    
    headers = {
        "Authorization": f"Bearer {GATEWAY_API_KEY}",
    }
    
    try:
        response = httpx.get(
            f"{GATEWAY_API_URL}/balances/{balance_id}",
            headers=headers
        )
        response.raise_for_status()
        
        balance_data = response.json()["data"]
        
        print(f"\n💰 Gateway Balance Info:")
        print(f"   Balance ID: {balance_id}")
        
        chain_balances = balance_data.get("chainBalances", [])
        if chain_balances:
            for chain_balance in chain_balances:
                chain = chain_balance.get("chain", "UNKNOWN")
                amount = chain_balance.get("amount", "0")
                # USDC uses 6 decimals
                readable = float(amount) / 1e6
                print(f"   {chain}: {readable:.6f} USDC ({amount} raw)")
        else:
            print("   No balances yet (empty)")
        
        return balance_data
        
    except httpx.HTTPStatusError as e:
        print(f"❌ API Error: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    print("🌉 Circle Gateway - Get Testnet USDC on Arc\n")
    
    # Check if balance ID already exists
    existing_balance_id = os.getenv("GATEWAY_BALANCE_ID")
    
    if existing_balance_id:
        print(f"ℹ️  Using existing Gateway Balance: {existing_balance_id}")
        balance_id = existing_balance_id
    else:
        # Create new Gateway balance
        balance_id = create_gateway_balance()
    
    # Get balance info
    get_balance_info(balance_id)
    
    print("\n📋 Next Steps:")
    print("1. Get testnet USDC on another chain (e.g., Ethereum Sepolia)")
    print("2. Deposit to Gateway balance (via API or Circle Portal UI)")
    print("3. Withdraw from Gateway to your Arc wallet address")
    print("\n💡 Tip: Use Circle Developer Portal UI for easier transfers")
    print("   Portal: https://developers.circle.com → Gateway")
