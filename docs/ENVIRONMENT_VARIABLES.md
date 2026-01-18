# Environment Variables Setup

Complete guide for configuring all environment variables needed for ClaimLedger.

## Backend Environment Variables

Create `backend/.env` file with the following:

```bash
# Database
DATABASE_URL=sqlite:///./claimledger.db
# For PostgreSQL: DATABASE_URL=postgresql://user:password@localhost/claimledger

# Circle Developer-Controlled Wallets
CIRCLE_WALLETS_API_KEY=your_api_key_here
CIRCLE_ENTITY_SECRET=your_entity_secret_here

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-change-in-production

# Circle Gateway (for x402 payments)
CIRCLE_GATEWAY_API_KEY=your_gateway_api_key_here

# Google AI (for agent evaluation)
GOOGLE_API_KEY=your_google_api_key_here

# Agent Model Configuration (optional)
# Default: gemini-2.0-flash
AGENT_MODEL=gemini-2.0-flash

# Arc Blockchain
ARC_RPC_URL=https://rpc.testnet.arc.network
CLAIM_ESCROW_ADDRESS=0x80794995149E5d26F22c36eD56B817CBd8E5d4Fa
USDC_ADDRESS=0x3600000000000000000000000000000000000000
```

## Frontend Environment Variables

Create `frontend/.env.local` file with the following:

```bash
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# No Circle SDK needed - all handled by backend!
```

## Circle Credentials Setup

### CIRCLE_WALLETS_API_KEY

**What it is:** API key for Circle Developer-Controlled Wallets (backend-only wallet management).

**How to get:**
1. Go to [Circle Developer Console](https://console.circle.com/signin)
2. Navigate to **API & Client Keys** → **Create a key**
3. Select **"API Key"** (not Client Key)
4. Choose **"Standard"** access (grants access to all Circle products) OR **"Wallets"** product
5. Copy the key immediately (format: `TEST_API_KEY:...` or `SAND_KEY_...` for Sandbox)

**Key format:**
- Sandbox/Testnet: `TEST_API_KEY:...` or `SAND_KEY_...`
- Production: `LIVE_API_KEY:...`

**Where to use:**
- `backend/.env`: `CIRCLE_WALLETS_API_KEY=TEST_API_KEY:...`
- Used by: `backend/src/services/developer_wallets.py`

### CIRCLE_ENTITY_SECRET

**What it is:** 32-byte (256-bit) cryptographic key required for Developer-Controlled Wallets. Used to encrypt wallet operations.

**How to generate:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**How to register:**
- See `docs/CIRCLE_ENTITY_SECRET_SETUP.md` for detailed instructions
- Or use: `python backend/scripts/register_entity_secret.py`
- Entity secret registers automatically when you create your first wallet

**Where to use:**
- `backend/.env`: `CIRCLE_ENTITY_SECRET=<64_character_hex_string>`
- Must be exactly 64 hexadecimal characters (32 bytes)

**Security:**
- Never commit to git (already in `.gitignore`)
- Keep a secure backup
- Required for all wallet operations

### CIRCLE_GATEWAY_API_KEY

**What it is:** API key for Circle Gateway (x402 micropayments and unified balances).

**How to get:**
1. Go to [Circle Developer Console](https://console.circle.com)
2. Navigate to **API & Client Keys**
3. Create **"API Key"** with **"Gateway"** product access
4. OR use the same Standard API key as Wallets (if Standard access)

**Key format:**
- Sandbox: `TEST_API_KEY:...` or `SAND_KEY_...`
- Production: `LIVE_API_KEY:...`

**Where to use:**
- `backend/.env`: `CIRCLE_GATEWAY_API_KEY=TEST_API_KEY:...`
- Used by: `backend/src/services/gateway.py` for x402 payments

**Note:** If you have a Standard API key, you can use the same key for both Wallets and Gateway:
```bash
CIRCLE_WALLETS_API_KEY=TEST_API_KEY:same_key_here
CIRCLE_GATEWAY_API_KEY=TEST_API_KEY:same_key_here
```

## JWT Authentication

### JWT_SECRET_KEY

**What it is:** Secret key for signing and verifying JWT tokens.

**How to generate:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Where to use:**
- `backend/.env`: `JWT_SECRET_KEY=<random_string>`
- Default: `"your-secret-key-change-in-production"` (change in production!)

**Security:**
- Use a strong random string in production
- Never commit to git
- Keep it secret

## Testnet Mode

**You can use ClaimLedger without Circle credentials!**

When Circle credentials are missing:
- Registration works (creates mock wallets)
- All features work for testing
- Mock wallets are deterministic based on user ID

**To enable real wallets:**
1. Add `CIRCLE_WALLETS_API_KEY` to `backend/.env`
2. Add `CIRCLE_ENTITY_SECRET` to `backend/.env`
3. Register entity secret (see `docs/CIRCLE_ENTITY_SECRET_SETUP.md`)
4. Real wallets will be created automatically

See `docs/TESTNET_MODE.md` for details.

## Circle API Keys: Wallets vs Gateway

**Two Different Circle Products = Two Different API Keys**

| Key | Product | Purpose | Used For |
|-----|---------|---------|----------|
| `CIRCLE_WALLETS_API_KEY` | **Circle Wallets** | Developer-Controlled wallet management | Creating wallets, backend wallet operations |
| `CIRCLE_GATEWAY_API_KEY` | **Circle Gateway** | Micropayments & unified balances | x402 payments, cross-chain USDC, micropayments |

**Can you use the same key?**
- ✅ **Yes**, if you create a **Standard** API key (grants access to all Circle products)
- ❌ **No**, if you create product-specific keys (Wallets-only or Gateway-only)

**Recommendation:** Create one Standard API key and use it for both:
```bash
CIRCLE_WALLETS_API_KEY=TEST_API_KEY:your_standard_key_here
CIRCLE_GATEWAY_API_KEY=TEST_API_KEY:your_standard_key_here
```

## Complete Setup Example

### Backend (`backend/.env`)

```bash
# Database
DATABASE_URL=sqlite:///./claimledger.db

# Circle Developer-Controlled Wallets
CIRCLE_WALLETS_API_KEY=TEST_API_KEY:your_key_here
CIRCLE_ENTITY_SECRET=your_64_char_hex_secret_here

# JWT Authentication
JWT_SECRET_KEY=your-jwt-secret-key

# Circle Gateway (x402 payments)
CIRCLE_GATEWAY_API_KEY=TEST_API_KEY:your_key_here

# Google AI (for agent evaluation)
GOOGLE_API_KEY=your_google_api_key_here

# Agent Model Configuration (optional)
# Default: gemini-2.0-flash
AGENT_MODEL=gemini-2.0-flash

# Arc Blockchain
ARC_RPC_URL=https://rpc.testnet.arc.network
CLAIM_ESCROW_ADDRESS=0x80794995149E5d26F22c36eD56B817CBd8E5d4Fa
USDC_ADDRESS=0x3600000000000000000000000000000000000000
```

### Frontend (`frontend/.env.local`)

```bash
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Quick Setup (Testnet Mode)

**For quick testing without Circle setup:**

1. Create `backend/.env`:
   ```bash
   DATABASE_URL=sqlite:///./claimledger.db
   JWT_SECRET_KEY=test-secret-key
   ```

2. Create `frontend/.env.local`:
   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. Start servers - mock wallets will be created automatically!

See `docs/TESTNET_MODE.md` for details.

## Verification

### Test Backend Environment

```bash
cd backend
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

keys = ['CIRCLE_WALLETS_API_KEY', 'CIRCLE_ENTITY_SECRET', 'JWT_SECRET_KEY']
for key in keys:
    value = os.getenv(key)
    if value:
        print(f'✅ {key}: {value[:10]}...')
    else:
        print(f'❌ {key}: NOT SET')
"
```

### Test Frontend Environment

```bash
cd frontend
node -e "
require('dotenv').config({ path: '.env.local' });
const apiUrl = process.env.NEXT_PUBLIC_API_URL;
console.log(apiUrl ? \`✅ NEXT_PUBLIC_API_URL: \${apiUrl}\` : '❌ NEXT_PUBLIC_API_URL: NOT SET');
"
```

## Troubleshooting

### "CIRCLE_WALLETS_API_KEY not configured"
- Set `CIRCLE_WALLETS_API_KEY` in `backend/.env`
- Restart backend server
- For testnet mode, this is optional (mock wallets will be used)

### "CIRCLE_ENTITY_SECRET not configured"
- Set `CIRCLE_ENTITY_SECRET` in `backend/.env`
- Must be 64 hex characters (32 bytes)
- For testnet mode, this is optional (mock wallets will be used)
- See `docs/CIRCLE_ENTITY_SECRET_SETUP.md` for registration

### "JWT_SECRET_KEY not configured"
- Set `JWT_SECRET_KEY` in `backend/.env`
- Has a default value for development, but change in production

### "Email already registered"
- User already exists in database
- Try logging in instead
- Or use a different email

### Invalid API key format
- Verify key starts with `TEST_API_KEY:` or `SAND_KEY_` for Sandbox
- Check for extra spaces or newlines
- Copy key exactly as shown in Circle Console

## Security Best Practices

1. **Never commit secrets to git:**
   - `.env` files are in `.gitignore`
   - Don't share keys in screenshots or public channels

2. **Use Sandbox for testing:**
   - Always use `TEST_API_KEY` or `SAND_KEY_` prefixed keys
   - Only use Production keys when ready for mainnet

3. **Rotate keys if compromised:**
   - Revoke immediately in Circle Console
   - Generate new key and update `.env` files

4. **Store Entity Secret securely:**
   - Keep in `.env` (gitignored)
   - Keep a backup in a secure password manager
   - Losing it means losing access to wallets

## References

- [Circle Developer Console](https://console.circle.com)
- [Circle Developer-Controlled Wallets Docs](https://developers.circle.com/wallets/dev-controlled)
- [Circle Gateway Docs](https://developers.circle.com/gateway)
- [Entity Secret Setup Guide](docs/CIRCLE_ENTITY_SECRET_SETUP.md)
- [Testnet Mode Guide](docs/TESTNET_MODE.md)
