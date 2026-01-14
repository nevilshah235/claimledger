# Backend Auth & Developer-Controlled Wallets Testing Guide

## Overview

The system now uses:
- **Our own authentication** (email/password with JWT)
- **Developer-Controlled Wallets** (backend-only, no frontend SDK)
- **Separate auth flows** for claimants and insurers

## Backend Testing

### 1. Install Dependencies

```bash
cd backend
uv pip install -e ".[dev]"
```

### 2. Set Environment Variables

Create `backend/.env`:
```bash
CIRCLE_WALLETS_API_KEY=your_api_key
CIRCLE_ENTITY_SECRET=your_32_byte_entity_secret
JWT_SECRET_KEY=your-jwt-secret-key
```

### 3. Test Registration (Claimant)

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "claimant@example.com",
    "password": "password123",
    "role": "claimant"
  }'
```

**Expected Response:**
```json
{
  "user_id": "...",
  "email": "claimant@example.com",
  "role": "claimant",
  "wallet_address": "0x...",
  "access_token": "eyJ..."
}
```

### 4. Test Registration (Insurer)

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "insurer@example.com",
    "password": "password123",
    "role": "insurer"
  }'
```

### 5. Test Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "claimant@example.com",
    "password": "password123"
  }'
```

### 6. Test Get Current User

```bash
# Use token from login response
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 7. Test Get Wallet Info

```bash
curl -X GET http://localhost:8000/auth/wallet \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Expected Response:**
```json
{
  "wallet_address": "0x...",
  "circle_wallet_id": "...",
  "wallet_set_id": "...",
  "blockchain": "ARC",
  "balance": {...}
}
```

### 8. Test Claim Submission (as Claimant)

```bash
curl -X POST http://localhost:8000/claims \
  -H "Authorization: Bearer CLAIMANT_TOKEN" \
  -F "claim_amount=1000.00" \
  -F "files=@test-document.pdf"
```

### 9. Test List Claims (as Insurer)

```bash
curl -X GET http://localhost:8000/claims \
  -H "Authorization: Bearer INSURER_TOKEN"
```

### 10. Test Settlement (as Insurer)

```bash
curl -X POST http://localhost:8000/blockchain/settle/CLAIM_ID \
  -H "Authorization: Bearer INSURER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Frontend Testing

### 1. Build Frontend

```bash
cd frontend
npm run build  # Should succeed without Circle SDK errors
```

### 2. Start Frontend

```bash
npm run dev
```

### 3. Test Flow

1. **Visit** `http://localhost:3000/claimant`
2. **Click** "Login as Claimant"
3. **Register** new account (email + password)
4. **Verify** wallet address is displayed automatically
5. **Submit** a claim
6. **Switch** to insurer view
7. **Login** as insurer
8. **View** all claims
9. **Settle** an approved claim

## Expected Behavior

- ✅ No Circle SDK build errors
- ✅ Registration automatically creates wallet
- ✅ Login returns wallet address
- ✅ Claims use authenticated user's wallet
- ✅ Insurers can view all claims
- ✅ Claimants see only their claims
- ✅ Settlement requires insurer role

## Troubleshooting

### "CIRCLE_ENTITY_SECRET not configured"
- Set `CIRCLE_ENTITY_SECRET` in `backend/.env`
- Must be 32 bytes (can generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)

### "CIRCLE_WALLETS_API_KEY not configured"
- Set `CIRCLE_WALLETS_API_KEY` in `backend/.env`
- Get from Circle Developer Console

### "Email already registered"
- User already exists, try login instead
- Or use different email

### "Invalid authentication credentials"
- Token expired or invalid
- Try logging in again

### Wallet creation fails
- Check Circle API key is valid
- Verify entity secret is registered with Circle
- Check Circle API logs in Developer Console
