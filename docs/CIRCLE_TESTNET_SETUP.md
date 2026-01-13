# Circle Wallets Testnet Setup - Step by Step 🚀

## Quick Start (5 Minutes)

If you're ready to get started quickly:

### Step 1: Get Circle API Key (2 minutes)
1. Go to: https://developers.circle.com
2. Sign up / Log in
3. Create application → Get **App ID**
4. Go to Wallets → Generate API Key → Get **API Key**
5. Copy both!

### Step 2: Set Up Environment (1 minute)
```bash
cd backend

# Create .env file if it doesn't exist
cat > .env << EOF
CIRCLE_WALLETS_API_KEY=SAND_KEY_your_key_here
CIRCLE_APP_ID=your_app_id_here
EOF
```

**Replace with your actual keys!**

### Step 3: Create Wallets (1 minute)
```bash
# Install dependencies (if not already)
rye sync

# Create wallets
rye run python scripts/create_circle_wallets.py
```

### Step 4: Get Testnet USDC (1 minute)
1. Copy your deployer wallet address from Step 3
2. Go to Circle Developer Portal → Faucet (or Discord)
3. Request testnet USDC to that address

### Step 5: Check Balance
```bash
rye run python scripts/check_balance.py
```

**For detailed instructions, continue reading below.**

---

## Overview

This guide helps you:
1. ✅ Set up Circle Developer Account
2. ✅ Get API keys (with priority order)
3. ✅ Create wallets using Circle Wallets API
4. ✅ Get testnet USDC for gas
5. ✅ Test wallets on Arc testnet

---

## Step 1: Create Circle Developer Account

### 1.1 Sign Up / Log In

1. Visit: https://developers.circle.com
2. Click "Sign Up" or "Log In"
3. Complete registration

### 1.2 Create Application

1. In Circle Developer Portal, click **"Create Application"**
2. Fill in:
   - **Name:** `ClaimLedger Testnet`
   - **Environment:** `Sandbox` (for testnet)
3. Click **"Create"**
4. **Save your App ID** - you'll need this!

**App ID looks like:** `12345678-1234-1234-1234-123456789abc`

---

## Step 2: Get API Keys (Priority Order)

For ClaimLedger, you need **3 keys from Circle** + **1 from Google**:

### Priority 1: Circle Wallets API Key ⭐ (Start Here!)

**Why:** To create wallets for users (claimants, insurers, agent)

**Steps:**
1. In Circle Developer Portal, go to **"Wallets"** section
2. Click **"API Keys"** or **"Generate Key"**
3. Select **"Sandbox"** environment (NOT Production)
4. Click **"Generate"** or **"Create Key"**
5. **Copy the key immediately** (you can't see it again!)
6. Save it as: `CIRCLE_WALLETS_API_KEY`

**Key format:** `SAND_KEY_abc123def456...` (starts with `SAND_KEY_`)

**Where to use:**
- `backend/.env`: `CIRCLE_WALLETS_API_KEY=SAND_KEY_...`
- Used by: `scripts/create_circle_wallets.py`

### Priority 2: Circle Gateway API Key

**Why:** For x402 micropayments and getting testnet USDC

**Steps:**
1. In Circle Developer Portal, go to **"Gateway"** section
2. Click **"API Keys"** or **"Generate Key"**
3. Select **"Sandbox"** environment
4. Click **"Generate"**
5. **Copy the key immediately**
6. Save it as: `CIRCLE_GATEWAY_API_KEY`

**Key format:** `SAND_KEY_xyz789...` (also starts with `SAND_KEY_`)

**Where to use:**
- `backend/.env`: `CIRCLE_GATEWAY_API_KEY=SAND_KEY_...`
- Used by: x402 micropayment service, Gateway balance scripts

### Priority 3: Circle App ID

**Why:** For frontend integration with Circle Wallets SDK

**Steps:**
1. In Circle Developer Portal, go to your application
2. Find **"App ID"** or **"Application ID"**
3. Copy it
4. Save it as: `CIRCLE_APP_ID`

**App ID format:** `12345678-1234-1234-1234-123456789abc` (UUID format)

**Where to use:**
- `backend/.env`: `CIRCLE_APP_ID=...`
- `frontend/.env.local`: `NEXT_PUBLIC_CIRCLE_APP_ID=...`

### Priority 4: Google AI/Gemini API Key

**Why:** For the AI agent that evaluates claims

**Steps:**
1. Go to: **https://aistudio.google.com**
2. Click **"Get API Key"** or **"Create API Key"**
3. Create new key or use existing project
4. **Copy the key**
5. Save it as: `GOOGLE_AI_API_KEY`

**Key format:** `AIza...` (starts with `AIza`)

**Where to use:**
- `backend/.env`: `GOOGLE_AI_API_KEY=AIza...`
- Used by: AI agent service (Google Agents Framework)

### Complete Environment Setup

**`backend/.env` File:**
```bash
# Circle Wallets API
CIRCLE_WALLETS_API_KEY=SAND_KEY_your_wallets_key_here
CIRCLE_APP_ID=your_app_id_here

# Circle Gateway API
CIRCLE_GATEWAY_API_KEY=SAND_KEY_your_gateway_key_here

# Google AI / Gemini
GOOGLE_AI_API_KEY=AIza_your_gemini_key_here

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/claimledger

# Arc Testnet
ARC_RPC_URL=https://rpc.testnet.arc.network
USDC_ADDRESS=0x3600000000000000000000000000000000000000
```

**`frontend/.env.local` File:**
```bash
# Circle App ID (for frontend SDK)
NEXT_PUBLIC_CIRCLE_APP_ID=your_app_id_here

# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Arc Testnet
NEXT_PUBLIC_ARC_RPC_URL=https://rpc.testnet.arc.network
NEXT_PUBLIC_ARC_CHAIN_ID=11124
```

### Priority Order (What to Do First)

**For Testing Wallets (Right Now):**
1. ✅ **Circle Wallets API Key** ← Start here!
2. ✅ **Circle App ID** ← Get this too

**Why:** These let you create wallets and test the setup

**For Full Functionality:**
3. ✅ **Circle Gateway API Key** ← Get this next
4. ✅ **Google AI API Key** ← Get this when building AI agent

---

## Step 3: Create Wallets Using Circle API

Let's create a Python script to interact with Circle Wallets API.

### 3.1 Install Required Packages

```bash
cd /Users/nevil/Documents/Projects/agenticai-arc/backend

# Install Circle SDK (if available) or use requests
rye add httpx python-dotenv
```

### 3.2 Create Wallet Creation Script

Create `scripts/create_circle_wallets.py`:

```python
#!/usr/bin/env python3
"""Create wallets using Circle Wallets API on testnet."""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# Circle API configuration
CIRCLE_API_KEY = os.getenv("CIRCLE_WALLETS_API_KEY")
CIRCLE_API_URL = "https://api.circle.com/v1/w3s"  # Sandbox/testnet

# Arc testnet chain ID
ARC_CHAIN_ID = 11124


def create_wallet(user_id: str, wallet_set_id: str = None):
    """Create a new wallet using Circle Wallets API."""
    
    headers = {
        "Authorization": f"Bearer {CIRCLE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Create wallet set (group of wallets) if not provided
    if not wallet_set_id:
        wallet_set_response = httpx.post(
            f"{CIRCLE_API_URL}/walletSets",
            headers=headers,
            json={"name": f"ClaimLedger-{user_id}"}
        )
        wallet_set_response.raise_for_status()
        wallet_set_id = wallet_set_response.json()["data"]["walletSet"]["id"]
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
        print("   Please add: CIRCLE_WALLETS_API_KEY=your_key_here")
        exit(1)
    
    print("🚀 Creating wallets using Circle Wallets API...\n")
    
    # Create deployer wallet
    print("1. Creating deployer wallet...")
    deployer = create_wallet("deployer")
    print(f"\n   Add to contracts/.env:")
    print(f"   DEPLOYER_WALLET_ADDRESS={deployer['address']}")
    print(f"   DEPLOYER_WALLET_ID={deployer['wallet_id']}\n")
    
    # Create agent wallet
    print("2. Creating agent wallet...")
    agent = create_wallet("agent", deployer['wallet_set_id'])
    print(f"\n   Add to backend/.env:")
    print(f"   AGENT_WALLET_ADDRESS={agent['address']}")
    print(f"   AGENT_WALLET_ID={agent['wallet_id']}\n")
    
    # Create insurer wallet
    print("3. Creating insurer wallet...")
    insurer = create_wallet("insurer", deployer['wallet_set_id'])
    print(f"\n   Add to backend/.env:")
    print(f"   INSURER_WALLET_ADDRESS={insurer['address']}")
    print(f"   INSURER_WALLET_ID={insurer['wallet_id']}\n")
    
    print("✅ All wallets created!")
    print("\n⚠️  Note: Circle Wallets are custodial (Circle manages keys)")
    print("   For deployment, you may still need a private key wallet.")
    print("   Use 'cast wallet new' for deployer if needed.")
```

### 3.3 Set Up Environment

Add to `backend/.env`:

```bash
# Circle Wallets API
CIRCLE_WALLETS_API_KEY=SAND_KEY_your_key_here

# Circle App ID (from Developer Portal)
CIRCLE_APP_ID=your_app_id_here
```

### 3.4 Run the Script

```bash
cd /Users/nevil/Documents/Projects/agenticai-arc/backend
rye run python scripts/create_circle_wallets.py
```

**Expected output:**
```
🚀 Creating wallets using Circle Wallets API...

1. Creating deployer wallet...
✅ Created wallet set: abc123...
✅ Created wallet:
   Wallet ID: def456...
   Address: 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
   Chain: ARC (testnet)
```

---

## Step 4: Get Testnet USDC for Gas

### Option A: Circle Testnet Faucet (If Available)

1. Check Circle Developer Portal for **"Faucet"** or **"Get Testnet USDC"**
2. Enter your wallet address
3. Request testnet USDC
4. Wait for confirmation

### Option B: Use Circle API to Check Balance

Create `scripts/check_balance.py`:

```python
#!/usr/bin/env python3
"""Check wallet balance on Arc testnet."""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

CIRCLE_API_KEY = os.getenv("CIRCLE_WALLETS_API_KEY")
WALLET_ID = os.getenv("DEPLOYER_WALLET_ID")  # Or AGENT_WALLET_ID, etc.

def check_balance():
    headers = {
        "Authorization": f"Bearer {CIRCLE_API_KEY}",
    }
    
    response = httpx.get(
        f"https://api.circle.com/v1/w3s/wallets/{WALLET_ID}/balances",
        headers=headers,
        params={"chain": "ARC"}
    )
    response.raise_for_status()
    
    balances = response.json()["data"]["tokenBalances"]
    
    print(f"💰 Wallet Balance (ARC testnet):")
    for balance in balances:
        token = balance.get("token", {})
        amount = balance.get("amount", "0")
        print(f"   {token.get('symbol', 'UNKNOWN')}: {amount}")
    
    return balances

if __name__ == "__main__":
    if not CIRCLE_API_KEY or not WALLET_ID:
        print("❌ Error: Missing CIRCLE_WALLETS_API_KEY or WALLET_ID")
        exit(1)
    
    check_balance()
```

### Option C: Request from Community

1. Join Circle Discord: https://discord.gg/circle
2. Ask in testnet channel for testnet USDC
3. Share your wallet address
4. Someone will send you testnet USDC

### Option D: Use cast to Generate Wallet and Get from Faucet

If Circle Wallets doesn't work for deployment, use `cast`:

```bash
# Generate wallet
cast wallet new

# Output:
# Address: 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
# Private key: 0x1234567890abcdef...

# Request testnet USDC to that address from:
# - Circle Developer Portal faucet
# - Circle Discord community
# - Arc testnet explorer (if faucet available)
```

---

## Step 5: Export Private Key (If Needed for Deployment)

**Important:** Circle Wallets are **custodial** (Circle manages keys). For contract deployment, you may need a private key.

### Option A: Use Circle Wallets (Custodial)
- ✅ Easy to use
- ✅ Secure (Circle manages keys)
- ❌ Can't export private key easily
- ❌ May not work with `forge script` deployment

### Option B: Use `cast wallet new` (Non-Custodial)
- ✅ Full control
- ✅ Can export private key
- ✅ Works with `forge script`
- ❌ You manage security

**For deployment, I recommend Option B:**

```bash
# Generate deployer wallet
cast wallet new

# Save to contracts/.env
PRIVATE_KEY=0x...your_private_key...
DEPLOYER_ADDRESS=0x...your_address...
```

**Then get testnet USDC to that address.**

---

## Step 6: Test Your Setup

### 6.1 Test Circle Wallets

```bash
cd /Users/nevil/Documents/Projects/agenticai-arc/backend
rye run python scripts/check_balance.py
```

### 6.2 Test cast Wallet (If Using)

```bash
# Check balance on Arc testnet
cast balance 0x...your_address... --rpc-url https://arc-testnet.rpc.circle.com

# Should show USDC balance (in wei, 18 decimals)
```

---

## Complete Setup Checklist

### Circle Developer Account
- [ ] Account created
- [ ] Application created
- [ ] App ID saved
- [ ] Wallets API key generated
- [ ] Gateway API key generated (optional)

### Wallets Created
- [ ] Deployer wallet (Circle or cast)
- [ ] Agent wallet (Circle)
- [ ] Insurer wallet (Circle)

### Testnet USDC
- [ ] Deployer wallet has USDC for gas
- [ ] Agent wallet has USDC (for receiving micropayments)
- [ ] Insurer wallet has USDC (for escrow deposits)

### Environment Variables
- [ ] `backend/.env` configured
- [ ] `contracts/.env` configured
- [ ] `frontend/.env.local` configured (with App ID)

---

## Troubleshooting

### Error: "Invalid API Key"
- Check API key is correct
- Make sure you're using **Sandbox** key (not Production)
- Verify key has proper permissions

### Error: "Insufficient funds"
- Get testnet USDC from faucet
- Check wallet address is correct
- Verify you're on Arc testnet (chain ID 11124)

### Error: "Wallet not found"
- Check wallet ID is correct
- Verify wallet was created on Arc testnet
- Check API key has access to that wallet

### Can't Export Private Key from Circle Wallets
- Circle Wallets are custodial (Circle manages keys)
- For deployment, use `cast wallet new` instead
- Use Circle Wallets for user wallets in your app

---

## Next Steps

Once you have:
1. ✅ Wallets created
2. ✅ Testnet USDC in deployer wallet
3. ✅ Environment variables set

You can proceed to:
- **Deploy ClaimEscrow contract** (Step 5-8 in DEPLOYMENT_GUIDE.md)
- **Test contract interactions**
- **Set up x402 micropayments**

---

## Quick Reference

### Circle API Endpoints (Sandbox/Testnet)
- **Base URL:** `https://api.circle.com/v1/w3s`
- **Create Wallet:** `POST /wallets`
- **Get Balance:** `GET /wallets/{id}/balances`
- **Create Wallet Set:** `POST /walletSets`

### Arc Testnet Info
- **RPC URL:** `https://arc-testnet.rpc.circle.com`
- **Chain ID:** `11124`
- **USDC Address:** `0x3600000000000000000000000000000000000000`
- **Explorer:** `https://testnet.arcscan.app`

---

## Need Help?

1. Check Circle Documentation: https://developers.circle.com
2. Join Circle Discord: https://discord.gg/circle
3. Check Arc Documentation: https://docs.arc.network

Ready to proceed! 🚀
