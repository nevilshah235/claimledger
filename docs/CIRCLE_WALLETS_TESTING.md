# Circle Wallets Integration - Testing Guide

## Status

✅ **Backend Integration Complete**
- Auth API endpoints implemented (`/auth/circle/*`)
- Circle Wallets service created
- UserWallet database model added
- All imports working correctly

✅ **Frontend Integration Complete**
- Circle SDK package installed (`@circle-fin/w3s-pw-web-sdk@1.1.11`)
- WalletConnect component updated with real SDK integration
- Build issues resolved (using Function constructor for dynamic import)
- All pages updated to handle wallet state

⚠️ **Environment Variables Required**

## Required Environment Variables

### Backend (`backend/.env`)

```bash
# Circle Wallets API Key (Sandbox/Testnet)
CIRCLE_WALLETS_API_KEY=SAND_KEY_your_key_here

# Circle App ID
CIRCLE_APP_ID=your-app-id-here
```

**How to get:**
1. Go to https://developers.circle.com
2. Create/select application
3. Go to Wallets section → Generate API Key (Sandbox)
4. Copy App ID from application settings

### Frontend (`frontend/.env.local`)

```bash
# Circle App ID (same as backend)
NEXT_PUBLIC_CIRCLE_APP_ID=your-app-id-here

# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Testing Steps

### 1. Backend API Testing

**Test Health:**
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

**Test Auth Init (without API key - will fail gracefully):**
```bash
curl -X POST http://localhost:8000/auth/circle/init \
  -H "Content-Type: application/json" \
  -d '{}'
# Expected: Error about missing CIRCLE_WALLETS_API_KEY
```

**Test Auth Init (with API key):**
```bash
# After setting CIRCLE_WALLETS_API_KEY in backend/.env
curl -X POST http://localhost:8000/auth/circle/init \
  -H "Content-Type: application/json" \
  -d '{}'
# Expected: { "user_id": "...", "user_token": "...", "challenge_id": "...", "app_id": "..." }
```

### 2. Frontend Testing

**Start Frontend:**
```bash
cd frontend
npm run dev
# Visit http://localhost:3000
```

**Test Wallet Connection:**
1. Click "Connect Wallet" button
2. Select "Circle Wallets" option
3. Should show Circle authentication UI (if API keys configured)
4. Or use "Demo Mode" for testing without Circle

**Expected Behavior:**
- ✅ Build completes successfully
- ✅ Dev server starts without errors
- ✅ WalletConnect component renders
- ✅ Demo mode works without API keys
- ✅ Circle mode shows error if API keys missing (graceful degradation)

### 3. End-to-End Flow Testing

**With Circle API Keys:**
1. Set `CIRCLE_WALLETS_API_KEY` and `CIRCLE_APP_ID` in backend/.env
2. Set `NEXT_PUBLIC_CIRCLE_APP_ID` in frontend/.env.local
3. Start backend: `cd backend && uvicorn src.main:app --reload`
4. Start frontend: `cd frontend && npm run dev`
5. Navigate to http://localhost:3000/claimant
6. Click "Connect Wallet" → "Circle Wallets"
7. Complete Circle authentication flow
8. Wallet address should appear in navbar
9. Submit a claim using the connected wallet

**Without Circle API Keys (Demo Mode):**
1. Start backend and frontend (no API keys needed)
2. Navigate to http://localhost:3000/claimant
3. Click "Connect Wallet" → "Demo Mode"
4. Mock wallet address appears
5. Can test claim submission flow

## Known Issues & Workarounds

### Issue: Circle SDK Build Errors

**Problem:** Circle SDK includes Node.js dependencies (undici, firebase) that Next.js can't bundle.

**Solution:** Using Function constructor for dynamic import:
```typescript
const importSDK = new Function('return import("@circle-fin/w3s-pw-web-sdk")');
const sdkModule = await importSDK();
```

This prevents Next.js from analyzing the import at build time.

### Issue: SDK Not Available

**Problem:** If Circle SDK fails to load, the app should gracefully fall back.

**Solution:** 
- Try-catch around SDK import
- Demo mode always available
- Clear error messages to user

## API Endpoints

### POST /auth/circle/init
Initialize Circle authentication challenge.

**Request:**
```json
{
  "user_id": "optional-user-id"
}
```

**Response:**
```json
{
  "user_id": "uuid",
  "user_token": "circle-user-token",
  "challenge_id": "challenge-id-for-sdk",
  "app_id": "circle-app-id"
}
```

### POST /auth/circle/complete
Complete authentication and store wallet mapping.

**Request:**
```json
{
  "user_token": "circle-user-token",
  "wallet_address": "0x...",
  "circle_wallet_id": "optional-wallet-id"
}
```

**Response:**
```json
{
  "success": true,
  "wallet_address": "0x...",
  "user_id": "uuid"
}
```

### GET /auth/circle/wallet
Get wallet address for authenticated user.

**Headers:**
```
X-User-Token: circle-user-token
```

**Response:**
```json
{
  "wallet_address": "0x...",
  "user_id": "uuid"
}
```

## Database

The `user_wallets` table is automatically created on backend startup via `init_db()`.

**Schema:**
- `id` (UUID) - Primary key
- `user_id` (String) - Circle user ID (unique)
- `wallet_address` (String) - Ethereum address
- `circle_wallet_id` (String) - Circle wallet ID (optional)
- `user_token` (String) - Circle user token
- `created_at`, `updated_at` - Timestamps

## Next Steps

1. **Get Circle API Keys** - Required for full integration
2. **Test Authentication Flow** - Verify Circle SDK works with real keys
3. **Test Claim Submission** - Verify wallet address is used correctly
4. **Test Settlement** - Verify insurer wallet connection works

## Troubleshooting

### "CIRCLE_WALLETS_API_KEY not configured"
- Set `CIRCLE_WALLETS_API_KEY` in `backend/.env`
- Restart backend server

### "NEXT_PUBLIC_CIRCLE_APP_ID not configured"
- Set `NEXT_PUBLIC_CIRCLE_APP_ID` in `frontend/.env.local`
- Restart frontend dev server

### "Circle SDK failed to load"
- Check browser console for detailed error
- Verify npm package is installed: `npm list @circle-fin/w3s-pw-web-sdk`
- Try clearing `.next` cache: `rm -rf .next && npm run dev`

### Build Errors
- If build fails, check `next.config.js` webpack configuration
- Ensure Function constructor import is used (not direct import)
