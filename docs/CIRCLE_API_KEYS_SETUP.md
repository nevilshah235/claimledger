# Circle Wallets API Key & App ID Setup Guide

## Overview

This guide walks you through creating the **Wallets API Key** and finding your **App ID** in the Circle Developer Console. These are required for the Circle Wallets SDK integration.

**What You Need:**
- `CIRCLE_WALLETS_API_KEY` - For backend API calls to Circle
- `CIRCLE_APP_ID` - For frontend SDK initialization

---

## Step 1: Sign Up / Log In to Circle Developer Console

1. **Visit:** https://console.circle.com/signin
   - If you don't have an account, click "Sign Up" and complete registration
   - If you have an account, log in with your credentials

2. **Select Environment:**
   - Make sure you're in **Sandbox** (testnet) environment
   - Look for environment selector at top of console
   - For hackathon/testing, use **Sandbox** (not Production)

---

## Step 2: Create API Key (Wallets API)

### Option A: Via API Keys Page

1. **Navigate to API Keys:**
   - In the Circle Developer Console, go to **"API & Client Keys"** section
   - Or visit directly: https://console.circle.com/api-keys

2. **Create New API Key:**
   - Click **"Create a key"** or **"Create New API Key"** button
   - Select **"API Key"** as the key type (not Client Key or Kit Key)

3. **Configure API Key:**
   - **Name:** Enter a descriptive name (e.g., "ClaimLedger Backend API Key")
   - **Key Type:** Choose one:
     - **Standard:** Grants read/write access to all APIs (recommended for testing)
     - **Restricted Access:** Limit to specific products/services
   - **IP Allowlist (Optional):** Add IP addresses for enhanced security

4. **Generate and Save:**
   - Click **"Create API Key"** or **"Generate"**
   - **⚠️ IMPORTANT:** Copy the API key immediately - it won't be shown again!
   - Format: `TEST_API_KEY:...` or `SAND_KEY_...` (for Sandbox)

5. **Save to Backend:**
   ```bash
   # Add to backend/.env
   CIRCLE_WALLETS_API_KEY=TEST_API_KEY:your_actual_key_here
   ```

### Option B: Via Application Settings

1. **Create/Select Application:**
   - In Developer Console, go to **"Applications"** section
   - Create a new application or select existing one
   - Name it (e.g., "ClaimLedger")

2. **Generate API Key:**
   - Within application settings, find **"API Keys"** section
   - Click **"Generate API Key"**
   - Follow steps above to configure and save

---

## Step 3: Get App ID

### Method 1: From Wallets Configurator (Recommended)

1. **Navigate to Configurator:**
   - In Circle Developer Console sidebar, go to:
     - **Wallets** → **User Controlled** → **Configurator**
   - Or navigate directly in the console

2. **Find App ID:**
   - The **App ID** will be displayed in the Configurator section
   - Format: UUID-like string (e.g., `12345678-1234-1234-1234-123456789abc`)
   - Copy this value

3. **Save to Both Backend and Frontend:**
   ```bash
   # backend/.env
   CIRCLE_APP_ID=12345678-1234-1234-1234-123456789abc
   
   # frontend/.env.local
   NEXT_PUBLIC_CIRCLE_APP_ID=12345678-1234-1234-1234-123456789abc
   ```

### Method 2: Via API (Programmatic)

If you already have an API key, you can retrieve App ID via API:

```bash
curl --request GET \
  --url https://api.circle.com/v1/w3s/config/entity \
  --header 'accept: application/json' \
  --header 'authorization: Bearer YOUR_API_KEY'
```

Response includes `appId` field.

### Method 3: From Application Details

1. **Go to Applications:**
   - In Developer Console, navigate to **"Applications"**
   - Click on your application

2. **View Application Details:**
   - The **App ID** (or **Application ID**) should be visible in the application details page
   - Copy this value

---

## Step 4: Verify Your Setup

### Test API Key

```bash
# Test your API key works
curl --request GET \
  --url https://api.circle.com/v1/w3s/wallets \
  --header 'accept: application/json' \
  --header 'authorization: Bearer YOUR_API_KEY'
```

**Expected Success Response:**
```json
{
  "data": {
    "wallets": []
  }
}
```

**Expected Error (if key invalid):**
```json
{
  "code": 401,
  "message": "Malformed authorization. Are the credentials properly encoded?"
}
```

### Test App ID

The App ID is used by the frontend SDK. You'll know it's correct when:
- Frontend SDK initializes without errors
- Circle authentication UI appears when connecting wallet

---

## Complete Environment Setup

### Backend (`backend/.env`)

```bash
# Circle Wallets API Key (Sandbox)
CIRCLE_WALLETS_API_KEY=TEST_API_KEY:ebb3ad72232624921abc4b162148bb84:019ef3358ef9cd6d08fc32csfe89a68d

# Circle App ID
CIRCLE_APP_ID=12345678-1234-1234-1234-123456789abc

# Other existing vars...
DATABASE_URL=sqlite:///./claimledger.db
GOOGLE_AI_API_KEY=your-google-key
# etc.
```

### Frontend (`frontend/.env.local`)

```bash
# Circle App ID (same as backend)
NEXT_PUBLIC_CIRCLE_APP_ID=12345678-1234-1234-1234-123456789abc

# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# Arc Testnet (if needed)
NEXT_PUBLIC_ARC_RPC_URL=https://arc-testnet.rpc.circle.com
NEXT_PUBLIC_ARC_CHAIN_ID=11124
```

---

## Key Types Reference

Based on Circle documentation, here's what each key type is for:

| Key Type | Purpose | Used For |
|----------|---------|----------|
| **API Key** | Server-side authentication | ✅ Backend API calls (what we need) |
| **Client Key** | Frontend SDK authentication | ❌ Not needed (we use App ID) |
| **Kit Key** | Circle Kits SDK | ❌ Not needed for Wallets |

**For User-Controlled Wallets:**
- ✅ **API Key** required (backend)
- ✅ **App ID** required (frontend SDK)
- ❌ Client Key not needed
- ❌ Kit Key not needed

---

## Important Notes

### API Key Format

**Sandbox/Testnet:**
```
TEST_API_KEY:ebb3ad72232624921abc4b162148bb84:019ef3358ef9cd6d08fc32csfe89a68d
```

**Production/Mainnet:**
```
LIVE_API_KEY:ebb3ad72232624921abc4b162148bb84:019ef3358ef9cd6d08fc32csfe89a68d
```

### Security Best Practices

1. **Never commit API keys to git:**
   - Keep them in `.env` files (already in `.gitignore`)
   - Don't share keys in screenshots or public channels

2. **Use Sandbox for testing:**
   - Always use `TEST_API_KEY` or `SAND_KEY_` prefixed keys for development
   - Only use Production keys when ready for mainnet

3. **Rotate keys if compromised:**
   - If a key is exposed, revoke it immediately in the console
   - Generate a new key and update your `.env` files

---

## Troubleshooting

### "API key not found" or "Invalid API key"
- Verify key is copied correctly (no extra spaces)
- Check you're using Sandbox key for testnet
- Ensure key starts with `TEST_API_KEY:` or `SAND_KEY_`

### "App ID not configured"
- Verify `CIRCLE_APP_ID` is set in backend `.env`
- Verify `NEXT_PUBLIC_CIRCLE_APP_ID` is set in frontend `.env.local`
- Restart both servers after adding env vars

### "Circle SDK failed to load"
- Check browser console for detailed error
- Verify App ID is correct format (UUID-like)
- Ensure frontend `.env.local` is loaded (restart dev server)

### Can't find App ID in Console
- Try Method 2 (API call) if Configurator doesn't show it
- Check application details page
- Contact Circle support if still not found

---

## Quick Reference Links

- **Circle Developer Console:** https://console.circle.com
- **API Keys Management:** https://console.circle.com/api-keys
- **Circle Documentation:** https://developers.circle.com
- **API Keys Docs:** https://developers.circle.com/w3s/keys
- **Circle Developer Account:** https://developers.circle.com/w3s/circle-developer-account

---

## Next Steps

Once you have both values:

1. ✅ Add `CIRCLE_WALLETS_API_KEY` to `backend/.env`
2. ✅ Add `CIRCLE_APP_ID` to both `backend/.env` and `frontend/.env.local`
3. ✅ Restart backend server
4. ✅ Restart frontend dev server
5. ✅ Test wallet connection in the app

The integration is ready to test once these environment variables are set!
