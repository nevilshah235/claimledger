#!/usr/bin/env python3
"""
Register Entity Secret with Circle.

This script registers your entity secret with Circle's Developer-Controlled Wallets API.
The entity secret must be registered before you can create wallets.

Usage:
    python scripts/register_entity_secret.py                    # Fetch key, encrypt, POST to Circle
    python scripts/register_entity_secret.py --print-ciphertext  # Only print ciphertext for manual paste
    python scripts/register_entity_secret.py --sdk              # Use Circle SDK (pip install circle-developer-controlled-wallets)

  --print-ciphertext   Generate and print the entity secret ciphertext (684 chars) for manual
                       registration in Circle Console → Wallets → Developer-Controlled → Configurator
                       https://console.circle.com/wallets/dev/configurator

  --sdk                Use circle.web3.utils.register_entity_secret_ciphertext from the
                       circle-developer-controlled-wallets package. Handles encryption, registration,
                       and optionally a recovery file. Install: pip install circle-developer-controlled-wallets

Requirements:
    - CIRCLE_WALLETS_API_KEY in environment or .env
    - CIRCLE_ENTITY_SECRET in environment or .env
"""

import argparse
import os
import sys
import asyncio
import httpx
import base64
from pathlib import Path
from dotenv import load_dotenv
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()


def register_via_sdk() -> bool:
    """
    Register entity secret using Circle's SDK: circle.web3.utils.register_entity_secret_ciphertext.
    Requires: pip install circle-developer-controlled-wallets
    """
    api_key = os.getenv("CIRCLE_WALLETS_API_KEY")
    entity_secret = os.getenv("CIRCLE_ENTITY_SECRET")

    if not api_key:
        print("❌ ERROR: CIRCLE_WALLETS_API_KEY not set")
        return False
    if not entity_secret:
        print("❌ ERROR: CIRCLE_ENTITY_SECRET not set")
        return False
    if len(entity_secret) != 64:
        print(f"❌ ERROR: Entity secret must be 64 hex chars, got {len(entity_secret)}")
        return False

    try:
        from circle.web3 import utils  # type: ignore[import-untyped]
    except ImportError:
        print("❌ circle-developer-controlled-wallets is not installed.")
        print("   Install it with: pip install circle-developer-controlled-wallets")
        return False

    print("=" * 60)
    print("REGISTERING ENTITY SECRET VIA CIRCLE SDK")
    print("=" * 60)
    print()
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"Entity Secret: {entity_secret[:8]}...{entity_secret[-8:]}")
    print()
    print("Calling utils.register_entity_secret_ciphertext(...)")
    print()

    try:
        result = utils.register_entity_secret_ciphertext(
            api_key=api_key,
            entity_secret=entity_secret,
            recoveryFileDownloadPath="",
        )
        print("✅ Result:")
        print(result)
        print()
        print("=" * 60)
        print("✅ REGISTRATION COMPLETE (via SDK)")
        print("=" * 60)
        return True
    except Exception as e:
        print(f"❌ SDK call failed: {e}")
        return False


async def register_entity_secret(print_ciphertext_only: bool = False):
    """Register entity secret with Circle. If print_ciphertext_only, only generate and print ciphertext."""
    api_key = os.getenv("CIRCLE_WALLETS_API_KEY")
    entity_secret = os.getenv("CIRCLE_ENTITY_SECRET")
    
    if not api_key:
        print("❌ ERROR: CIRCLE_WALLETS_API_KEY not set")
        print("   Set it in backend/.env or as environment variable")
        return False
    
    if not entity_secret:
        print("❌ ERROR: CIRCLE_ENTITY_SECRET not set")
        print("   Set it in backend/.env or as environment variable")
        return False
    
    # Validate entity secret is 32 bytes (64 hex characters)
    if len(entity_secret) != 64:
        print(f"❌ ERROR: Entity secret must be 32 bytes (64 hex chars)")
        print(f"   Current length: {len(entity_secret)}")
        return False
    
    try:
        # Convert hex string to bytes
        entity_secret_bytes = bytes.fromhex(entity_secret)
        if len(entity_secret_bytes) != 32:
            raise ValueError("Invalid entity secret length")
    except ValueError as e:
        print(f"❌ ERROR: Invalid entity secret format: {e}")
        print("   Entity secret must be a 64-character hexadecimal string")
        return False
    
    print("=" * 60)
    print("REGISTERING ENTITY SECRET WITH CIRCLE")
    print("=" * 60)
    print()
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"Entity Secret: {entity_secret}")
    print()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Get Circle's public key
        print("Step 1: Fetching Circle's public key...")
        try:
            response = await client.get(
                "https://api.circle.com/v1/w3s/config/entity/publicKey",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            public_key_data = response.json()["data"]
            public_key_pem = public_key_data["publicKey"]
            print("✅ Public key retrieved")
        except httpx.HTTPStatusError as e:
            print(f"❌ Failed to get public key: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        # Step 2: Encrypt entity secret
        print()
        print("Step 2: Encrypting entity secret...")
        try:
            public_key = RSA.import_key(public_key_pem)
            # Circle requires RSA-OAEP with SHA-256 for both OAEP hash and MGF1
            cipher = PKCS1_OAEP.new(public_key, hashAlgo=SHA256)
            encrypted_secret = cipher.encrypt(entity_secret_bytes)
            entity_secret_ciphertext = base64.b64encode(encrypted_secret).decode('utf-8')
            print("✅ Entity secret encrypted")
            # Circle expects 684 chars (4096-bit RSA: 512 bytes → base64)
            print(f"   Ciphertext length: {len(entity_secret_ciphertext)} chars (Circle expects 684)")
        except Exception as e:
            print(f"❌ Encryption failed: {e}")
            return False

        if print_ciphertext_only:
            print()
            print("=" * 60)
            print("ENTITY SECRET CIPHERTEXT (copy for Circle Configurator)")
            print("=" * 60)
            print()
            print("Paste this into: Circle Console → Wallets → Developer-Controlled → Configurator")
            print("https://console.circle.com/wallets/dev/configurator")
            print()
            print(entity_secret_ciphertext)
            print()
            print("=" * 60)
            return True

        # Step 3: Register with Circle
        print()
        print("Step 3: Registering with Circle...")
        try:
            import uuid
            
            # Register entity secret using Circle's API
            # Endpoint: POST /v1/w3s/config/entity/secret
            idempotency_key = str(uuid.uuid4())
            
            response = await client.post(
                "https://api.circle.com/v1/w3s/config/entity/secret",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "idempotencyKey": idempotency_key,
                    "entitySecretCiphertext": entity_secret_ciphertext
                }
            )
            
            if response.status_code == 200 or response.status_code == 201:
                print("✅ Entity secret registered successfully!")
                print()
                data = response.json()
                print(f"Response: {data}")
                print()
                print("=" * 60)
                print("✅ REGISTRATION COMPLETE")
                print("=" * 60)
                print()
                print("Your entity secret is now registered with Circle.")
                print("You can now create wallets using the Developer-Controlled Wallets API.")
                return True
            elif response.status_code == 400:
                # Might already be registered or invalid format
                error_data = response.json()
                error_msg = error_data.get("message", response.text)
                print(f"⚠️  Registration response: {response.status_code}")
                print(f"   {error_msg}")
                print()
                if "already" in error_msg.lower() or "exists" in error_msg.lower():
                    print("✅ Entity secret appears to already be registered!")
                    print("   Try creating a wallet to verify.")
                    return True
                else:
                    print("This might indicate:")
                    print("- Entity secret format issue")
                    print("- API key permissions")
                    print("- Check Circle API documentation")
                    return False
            else:
                print(f"⚠️  Unexpected response: {response.status_code}")
                print(f"   {response.text}")
                print()
                print("Note: Some Circle setups register entity secret automatically")
                print("when you create your first wallet set.")
                print()
                print("Try creating a wallet - if it works, registration succeeded.")
                return True
                
        except httpx.HTTPStatusError as e:
            print(f"❌ Registration failed: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
            print()
            if e.response.status_code == 400:
                print("This might mean:")
                print("- Entity secret is already registered")
                print("- Entity secret format is incorrect")
                print("- Check Circle API documentation for latest requirements")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Register entity secret with Circle (or print ciphertext for manual paste).")
    parser.add_argument(
        "--print-ciphertext",
        action="store_true",
        help="Only generate and print the entity secret ciphertext for manual paste in Circle Configurator",
    )
    parser.add_argument(
        "--sdk",
        action="store_true",
        help="Use circle.web3.utils.register_entity_secret_ciphertext (requires circle-developer-controlled-wallets)",
    )
    args = parser.parse_args()

    if args.sdk:
        success = register_via_sdk()
    else:
        success = asyncio.run(register_entity_secret(print_ciphertext_only=args.print_ciphertext))
    sys.exit(0 if success else 1)
