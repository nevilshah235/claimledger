# Testnet Mode - Development Without Circle Registration

## Overview

For development and testing, you can use ClaimLedger **without registering an Entity Secret with Circle**. The system will automatically create mock wallet addresses that work for testing.

## How It Works

When Circle credentials are missing or entity secret isn't registered:

1. **User registration succeeds** - Account is created normally
2. **Mock wallet generated** - A deterministic mock wallet address is created based on user ID
3. **All features work** - Claims, evaluations, and settlements work with mock addresses
4. **Real wallets later** - When Circle is configured, real wallets can be created

## Mock Wallet Format

Mock wallets are generated as:
```
0x{sha256(user_id + email)[:40]}
```

This ensures:
- ✅ Valid Ethereum address format
- ✅ Deterministic (same user = same address)
- ✅ Unique per user
- ✅ Works for all blockchain operations in testnet

## Usage

### Without Circle Credentials

Just register users normally - mock wallets are created automatically:

```bash
# Registration works without Circle
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "role": "claimant"
  }'
```

**Response:**
```json
{
  "user_id": "...",
  "email": "user@example.com",
  "role": "claimant",
  "wallet_address": "0x1234...abcd",  // Mock wallet
  "access_token": "..."
}
```

### With Circle Credentials

When you add Circle credentials to `.env`:
- Real wallets are created automatically
- Mock wallets are replaced with Circle wallets
- All existing functionality continues to work

## Environment Variables

**Testnet Mode (No Circle):**
```bash
# No Circle credentials needed
# JWT_SECRET_KEY=your-secret-key  # Optional, has default
```

**Production Mode (With Circle):**
```bash
CIRCLE_WALLETS_API_KEY=your_api_key
CIRCLE_ENTITY_SECRET=your_entity_secret
JWT_SECRET_KEY=your-secret-key
```

## Testing Flow

1. **Start backend** (no Circle credentials needed)
2. **Register users** - Mock wallets created automatically
3. **Submit claims** - Uses mock wallet addresses
4. **Test all features** - Everything works with mock wallets
5. **Add Circle later** - Real wallets created for new users

## Limitations

Mock wallets:
- ✅ Work for all ClaimLedger features
- ✅ Valid Ethereum address format
- ❌ Cannot receive real USDC
- ❌ Cannot interact with real blockchain
- ❌ Not registered with Circle

For real blockchain operations, configure Circle credentials.

## Migration to Real Wallets

When ready to use real wallets:

1. Add Circle credentials to `backend/.env`
2. Register entity secret (see `CIRCLE_ENTITY_SECRET_SETUP.md`)
3. New user registrations will create real wallets
4. Existing users keep mock wallets (or can be migrated)

## Benefits

- **Fast development** - No Circle setup required
- **Full testing** - All features work with mocks
- **Easy migration** - Add Circle when ready
- **No registration needed** - Start testing immediately
