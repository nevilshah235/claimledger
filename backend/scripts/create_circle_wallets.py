#!/usr/bin/env python3
"""Create wallets using Circle Wallets API on testnet."""

import os
import sys
import httpx
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

# Circle API configuration
CIRCLE_API_KEY = os.getenv("CIRCLE_WALLETS_API_KEY")
CIRCLE_API_URL = "https://api.circle.com/v1/w3s"  # Sandbox/testnet

# Arc testnet chain ID
ARC_CHAIN_ID = 11124


def create_wallet_set(name: str):
    """Create a wallet set (group of wallets)."""
    headers = {
        "Authorization": f"Bearer {CIRCLE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = httpx.post(
        f"{CIRCLE_API_URL}/walletSets",
        headers=headers,
        json={"name": name}
    )
    response.raise_for_status()
    
    wallet_set_id = response.json()["data"]["walletSet"]["id"]
    return wallet_set_id


def create_wallet(user_id: str, wallet_set_id: str = None):
    """Create a new wallet using Circle Wallets API."""
    
    headers = {
        "Authorization": f"Bearer {CIRCLE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Create wallet set (group of wallets) if not provided
    if not wallet_set_id:
        wallet_set_id = create_wallet_set(f"ClaimLedger-{user_id}")
        print(f"✅ Created wallet set: {wallet_set_id}")
    
    # Create wallet
    wallet_response = httpx.post(
        f"{CIRCLE_API_URL}/wallets",
        headers=headers,
        json={
            "blockchains": ["ARC"],  # Arc testnet
            "walletSetId": wallet_set_id
        }
    )
    wallet_response.raise_for_status()
    
    wallet_data = wallet_response.json()["data"]["wallet"]
    wallet_id = wallet_data["id"]
    wallet_address = wallet_data["address"]
    
    print(f"✅ Created wallet:")
    print(f"   Wallet ID: {wallet_id}")
    print(f"   Address: {wallet_address}")
    print(f"   Chain: ARC (testnet)")
    
    return {
        "wallet_id": wallet_id,
        "address": wallet_address,
        "wallet_set_id": wallet_set_id
    }


def get_wallet_balance(wallet_id: str):
    """Get wallet balance on Arc testnet."""
    
    headers = {
        "Authorization": f"Bearer {CIRCLE_API_KEY}",
    }
    
    response = httpx.get(
        f"{CIRCLE_API_URL}/wallets/{wallet_id}/balances",
        headers=headers,
        params={"chain": "ARC"}
    )
    response.raise_for_status()
    
    balances = response.json()["data"]["tokenBalances"]
    return balances


if __name__ == "__main__":
    if not CIRCLE_API_KEY:
        print("❌ Error: CIRCLE_WALLETS_API_KEY not found in .env")
        print("   Please add to backend/.env:")
        print("   CIRCLE_WALLETS_API_KEY=SAND_KEY_your_key_here")
        print("\n   Get your API key from: https://developers.circle.com")
        sys.exit(1)
    
    print("🚀 Creating wallets using Circle Wallets API...\n")
    
    try:
        # Create deployer wallet
        print("1. Creating deployer wallet...")
        deployer = create_wallet("deployer")
        print(f"\n   📝 Add to contracts/.env:")
        print(f"   DEPLOYER_WALLET_ADDRESS={deployer['address']}")
        print(f"   DEPLOYER_WALLET_ID={deployer['wallet_id']}\n")
        
        # Create agent wallet
        print("2. Creating agent wallet...")
        agent = create_wallet("agent", deployer['wallet_set_id'])
        print(f"\n   📝 Add to backend/.env:")
        print(f"   AGENT_WALLET_ADDRESS={agent['address']}")
        print(f"   AGENT_WALLET_ID={agent['wallet_id']}\n")
        
        # Create insurer wallet
        print("3. Creating insurer wallet...")
        insurer = create_wallet("insurer", deployer['wallet_set_id'])
        print(f"\n   📝 Add to backend/.env:")
        print(f"   INSURER_WALLET_ADDRESS={insurer['address']}")
        print(f"   INSURER_WALLET_ID={insurer['wallet_id']}\n")
        
        print("✅ All wallets created successfully!")
        print("\n⚠️  Important Notes:")
        print("   - Circle Wallets are custodial (Circle manages keys)")
        print("   - For contract deployment, you may need a private key wallet")
        print("   - Use 'cast wallet new' if you need private key for deployment")
        print("   - Get testnet USDC to these addresses from Circle faucet")
        
    except httpx.HTTPStatusError as e:
        print(f"\n❌ API Error: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
        print("\n   Check:")
        print("   - API key is correct")
        print("   - You're using Sandbox/testnet key (not Production)")
        print("   - API key has proper permissions")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
