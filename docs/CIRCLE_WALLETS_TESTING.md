# Circle Wallets Integration - Testing Guide

## Status

✅ **Backend Integration Complete**
- Developer-Controlled Wallets service implemented
- Auth API endpoints (`/auth/register`, `/auth/login`, `/auth/me`, `/auth/wallet`)
- Wallet auto-provision on user registration
- Testnet mode with mock wallets (works without Circle credentials)
- All imports working correctly

✅ **Frontend Integration Complete**
- Custom authentication system (no Circle SDK needed)
- AuthModal component for login/register
- WalletDisplay component for wallet info
- All pages updated to use backend auth
- Build succeeds without Circle SDK

⚠️ **Circle Credentials Optional**
- Testnet mode works without Circle credentials (mock wallets)
- Real wallets require `CIRCLE_WALLETS_API_KEY` and `CIRCLE_ENTITY_SECRET`

## Current Implementation

**We are using: Developer-Controlled Wallets**

- Backend-only wallet management
- No frontend Circle SDK required
- Wallets created automatically on user registration
- Entity secret encryption with RSA-OAEP
- Testnet mode for development/testing

## Required Environment Variables

### Backend (`backend/.env`)

```bash
# Minimum for testnet mode (mock wallets)
DATABASE_URL=sqlite:///./claimledger.db
JWT_SECRET_KEY=your-secret-key

# Optional: For real wallets
CIRCLE_WALLETS_API_KEY=your_api_key_here
CIRCLE_ENTITY_SECRET=your_entity_secret_here
```

**How to get Circle credentials:**
- See `docs/ENVIRONMENT_VARIABLES.md` for detailed setup
- See `docs/CIRCLE_ENTITY_SECRET_SETUP.md` for entity secret registration

### Frontend (`frontend/.env.local`)

```bash
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# No Circle SDK needed - all handled by backend!
```

## Testing Steps

### 1. Backend API Testing

**Test Health:**
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

**Test Registration (Testnet Mode - Mock Wallet):**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123",
    "role": "claimant"
  }'
```

**Expected (testnet mode):**
```json
{
  "user_id": "...",
  "email": "test@example.com",
  "role": "claimant",
  "wallet_address": "0x1234...abcd",
  "access_token": "eyJ..."
}
```

**Expected (with Circle - real wallet):**
```json
{
  "user_id": "...",
  "email": "test@example.com",
  "role": "claimant",
  "wallet_address": "0x...",
  "access_token": "eyJ..."
}
```

**Test Login:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123"
  }'
```

**Test Get Wallet:**
```bash
# Use token from registration/login
curl http://localhost:8000/auth/wallet \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Expected:**
```json
{
  "wallet_address": "0x...",
  "circle_wallet_id": "...",
  "wallet_set_id": "...",
  "blockchain": "ARC",
  "balance": {...}
}
```

### 2. Frontend Testing

**Start Frontend:**
```bash
cd frontend
npm run dev
# Visit http://localhost:3000
```

**Test Authentication Flow:**
1. Click "Login as Claimant" button
2. Register new account (email + password)
3. Wallet address appears automatically
4. Can submit claims immediately

**Expected Behavior:**
- ✅ Build completes successfully
- ✅ Dev server starts without errors
- ✅ AuthModal component works
- ✅ WalletDisplay shows wallet address
- ✅ Testnet mode works without Circle credentials
- ✅ Real wallets work when Circle is configured

### 3. End-to-End Flow Testing

**Testnet Mode (No Circle Credentials):**
1. Start backend and frontend (no Circle credentials needed)
2. Navigate to http://localhost:3000/claimant
3. Click "Login as Claimant" → Register
4. Mock wallet address appears automatically
5. Submit a claim - uses mock wallet
6. All features work for testing

**With Circle Credentials (Real Wallets):**
1. Set `CIRCLE_WALLETS_API_KEY` and `CIRCLE_ENTITY_SECRET` in `backend/.env`
2. Register entity secret (see `docs/CIRCLE_ENTITY_SECRET_SETUP.md`)
3. Start backend: `cd backend && python -m uvicorn src.main:app --reload`
4. Start frontend: `cd frontend && npm run dev`
5. Navigate to http://localhost:3000/claimant
6. Click "Login as Claimant" → Register
7. Real wallet created automatically via Circle API
8. Wallet address appears (real Circle wallet)
9. Submit a claim using the real wallet

## API Endpoints

### POST /auth/register
Register new user and automatically create wallet.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "role": "claimant"
}
```

**Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "role": "claimant",
  "wallet_address": "0x...",
  "access_token": "eyJ..."
}
```

### POST /auth/login
Login existing user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "role": "claimant",
  "wallet_address": "0x...",
  "access_token": "eyJ..."
}
```

### GET /auth/me
Get current authenticated user info.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "role": "claimant",
  "wallet_address": "0x..."
}
```

### GET /auth/wallet
Get wallet information for authenticated user.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "wallet_address": "0x...",
  "circle_wallet_id": "...",
  "wallet_set_id": "...",
  "blockchain": "ARC",
  "balance": {...}
}
```

## Database

The `users` and `user_wallets` tables are automatically created on backend startup.

**Users Schema:**
- `id` (UUID) - Primary key
- `email` (String) - Unique, indexed
- `password_hash` (String) - bcrypt hash
- `role` (String) - "claimant" or "insurer"
- `created_at`, `updated_at` - Timestamps

**UserWallets Schema:**
- `id` (UUID) - Primary key
- `user_id` (UUID) - Foreign key to users.id (unique)
- `wallet_address` (String) - Ethereum address
- `circle_wallet_id` (String) - Circle wallet ID
- `wallet_set_id` (String) - Circle wallet set ID (optional)
- `created_at`, `updated_at` - Timestamps

## Testnet Mode

**Works without Circle credentials!**

When Circle credentials are missing:
- Registration succeeds
- Mock wallets are generated automatically
- All features work for testing
- Real wallets created when Circle is configured

See `docs/TESTNET_MODE.md` for details.

## Next Steps

1. **Test Registration** - Verify users can register and get wallets
2. **Test Login** - Verify JWT tokens work
3. **Test Claim Submission** - Verify authenticated user's wallet is used
4. **Test Insurer Flow** - Register as insurer, view all claims
5. **Test Settlement** - Verify insurer can settle claims

## Troubleshooting

### "CIRCLE_ENTITY_SECRET not configured"
- This is **expected** in testnet mode
- Mock wallets will be created automatically
- To use real wallets, see `docs/CIRCLE_ENTITY_SECRET_SETUP.md`

### "CIRCLE_WALLETS_API_KEY not configured"
- Set `CIRCLE_WALLETS_API_KEY` in `backend/.env`
- Restart backend server
- For testnet mode, this is optional

### "Email already registered"
- User already exists
- Try logging in instead
- Or use a different email

### "Invalid authentication credentials"
- Token expired or invalid
- Login again to get a new token
- Check token is included in `Authorization: Bearer <token>` header

### Wallet creation fails
- Check Circle API key is valid
- Verify entity secret is registered with Circle
- Check Circle API logs in Developer Console
- For testnet mode, mock wallets are used automatically

## Legacy Endpoints (Deprecated)

The following endpoints are kept for backward compatibility but are deprecated:

- `POST /auth/circle/init` - Use `/auth/register` instead
- `POST /auth/circle/complete` - Use `/auth/register` instead
- `GET /auth/circle/wallet` - Use `/auth/wallet` with Bearer token instead

## References

- **Environment Setup:** `docs/ENVIRONMENT_VARIABLES.md`
- **Backend Auth Testing:** `docs/BACKEND_AUTH_TESTING.md`
- **Testnet Mode:** `docs/TESTNET_MODE.md`
- **Entity Secret Setup:** `docs/CIRCLE_ENTITY_SECRET_SETUP.md`
- **Circle Developer-Controlled Wallets:** https://developers.circle.com/wallets/dev-controlled
