#!/usr/bin/env python3
"""Check wallet balance on Arc testnet using Circle API."""

import os
import sys
import httpx
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

CIRCLE_API_KEY = os.getenv("CIRCLE_WALLETS_API_KEY")
WALLET_ID = os.getenv("DEPLOYER_WALLET_ID")  # Can override with command line arg


def check_balance(wallet_id: str = None):
    """Check wallet balance on Arc testnet."""
    
    if not wallet_id:
        wallet_id = WALLET_ID
    
    if not CIRCLE_API_KEY:
        print("❌ Error: CIRCLE_WALLETS_API_KEY not found in .env")
        sys.exit(1)
    
    if not wallet_id:
        print("❌ Error: WALLET_ID not found")
        print("   Set DEPLOYER_WALLET_ID in .env or pass as argument")
        sys.exit(1)
    
    headers = {
        "Authorization": f"Bearer {CIRCLE_API_KEY}",
    }
    
    try:
        response = httpx.get(
            f"https://api.circle.com/v1/w3s/wallets/{wallet_id}/balances",
            headers=headers,
            params={"chain": "ARC"}
        )
        response.raise_for_status()
        
        balances = response.json()["data"]["tokenBalances"]
        
        print(f"💰 Wallet Balance (ARC testnet):")
        print(f"   Wallet ID: {wallet_id}\n")
        
        if not balances:
            print("   No balances found (wallet is empty)")
            print("\n   💡 Get testnet USDC from:")
            print("      - Circle Developer Portal faucet")
            print("      - Circle Discord community")
        else:
            for balance in balances:
                token = balance.get("token", {})
                amount = balance.get("amount", "0")
                symbol = token.get("symbol", "UNKNOWN")
                decimals = token.get("decimals", 18)
                
                # Convert to readable format
                if decimals == 18:
                    # Native USDC (gas) - 18 decimals
                    readable_amount = float(amount) / 1e18
                elif decimals == 6:
                    # ERC-20 USDC - 6 decimals
                    readable_amount = float(amount) / 1e6
                else:
                    readable_amount = float(amount) / (10 ** decimals)
                
                print(f"   {symbol}: {readable_amount:,.6f} ({amount} raw)")
        
        return balances
        
    except httpx.HTTPStatusError as e:
        print(f"❌ API Error: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Allow wallet ID as command line argument
    wallet_id = sys.argv[1] if len(sys.argv) > 1 else None
    check_balance(wallet_id)
