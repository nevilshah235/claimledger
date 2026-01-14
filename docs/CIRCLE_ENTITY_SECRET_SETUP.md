# Circle Entity Secret Setup Guide

## Overview

The Entity Secret is a 32-byte (256-bit) cryptographic key required for Circle's Developer-Controlled Wallets. It's used to encrypt wallet operations and must be registered with Circle before creating wallets.

## Step 1: Generate Entity Secret

Run this command to generate a secure 32-byte entity secret:

```bash
cd backend
python -c "import secrets; print(secrets.token_hex(32))"
```

**Example output:**
```
a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
```

**⚠️ IMPORTANT:** Save this secret immediately! You'll need it for all wallet operations.

## Step 2: Add to Environment

Add the generated secret to `backend/.env`:

```bash
CIRCLE_ENTITY_SECRET=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
```

## Step 3: Register with Circle

### Option A: Automatic Registration (Recommended)

Entity secret is automatically registered when you create your first wallet set. Just try registering a user - if wallet creation succeeds, registration worked.

### Option B: Manual Registration Script

Use the provided script to explicitly register:

```bash
cd backend
python scripts/register_entity_secret.py
```

The script will:
1. Fetch Circle's public key
2. Encrypt your entity secret using RSA-OAEP
3. Register it with Circle
4. Confirm registration success

### Option C: Manual API Registration

Register directly via Circle's API:

```python
import httpx
import uuid
import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

async def register_entity_secret(api_key, entity_secret_hex):
    async with httpx.AsyncClient() as client:
        # 1. Get Circle's public key
        response = await client.get(
            "https://api.circle.com/v1/config/entity/publicKey",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        public_key = response.json()["data"]["publicKey"]
        
        # 2. Encrypt entity secret
        rsa_key = RSA.import_key(public_key)
        cipher = PKCS1_OAEP.new(rsa_key)
        encrypted = cipher.encrypt(bytes.fromhex(entity_secret_hex))
        ciphertext = base64.b64encode(encrypted).decode()
        
        # 3. Register
        response = await client.post(
            "https://api.circle.com/v1/w3s/config/entity/secret",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "idempotencyKey": str(uuid.uuid4()),
                "entitySecretCiphertext": ciphertext
            }
        )
        return response.json()
```

## Step 4: Verify Registration

After registration, test wallet creation:

```bash
# Try registering a user - wallet should be created automatically
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123",
    "role": "claimant"
  }'
```

If you get a real wallet address (not `0x0000...`), registration succeeded!

## Troubleshooting

### "CIRCLE_ENTITY_SECRET not configured"
- Make sure it's set in `backend/.env`
- Restart the backend server
- Check the secret is exactly 64 hex characters (32 bytes)

### "Entity secret registration failed"
- Verify your `CIRCLE_WALLETS_API_KEY` is correct
- Check the secret is valid hex (0-9, a-f only)
- Entity secret may already be registered (try creating a wallet)

### "Invalid entity secret format"
- Must be exactly 64 hexadecimal characters
- No spaces or special characters
- Example: `a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456`

## Security Notes

- **Never commit** the entity secret to git
- Store it securely (use `.env` which is in `.gitignore`)
- Keep a backup in a secure password manager
- If compromised, generate a new one and re-register
- The entity secret is required for all wallet operations - losing it means losing access to wallets

## References

- [Circle Developer-Controlled Wallets Docs](https://developers.circle.com/wallets/dev-controlled)
- [Entity Secret Management](https://developers.circle.com/wallets/dev-controlled/entity-secret-management)
