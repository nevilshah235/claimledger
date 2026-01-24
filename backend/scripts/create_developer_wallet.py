#!/usr/bin/env python3
"""
Create a developer (programmatic) wallet for auto-settle.

Generates a new EVM keypair. Use the private key as AUTO_SETTLE_PRIVATE_KEY
and fund the address with USDC and ARC on the Arc network.

Usage:
    python scripts/create_developer_wallet.py

Requires: eth_account (install via: pip install eth-account, or use a env that has web3)
"""

import sys
from pathlib import Path

# Add backend root so we can run from repo root or backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from eth_account import Account
except ImportError:
    print(
        "eth_account is required. Install with:\n"
        "  pip install eth-account\n"
        "  # or: uv add eth-account  (in backend)\n"
        "The backend's web3 dependency may already provide it; ensure your venv is activated."
    )
    sys.exit(1)


def main() -> None:
    acct = Account.create()
    pk_hex = acct.key.hex()
    # Support 0x-prefixed for .env (common convention)
    pk_with_prefix = "0x" + pk_hex if not pk_hex.startswith("0x") else pk_hex

    print("Developer (auto-settle) wallet created.\n")
    print("Private key (use for AUTO_SETTLE_PRIVATE_KEY in backend/.env):")
    print(pk_with_prefix)
    print()
    print("Address (fund with USDC and ARC on Arc testnet):")
    print(acct.address)
    print()
    print("Next steps:")
    print("  1. Add to backend/.env:")
    print(f"     AUTO_SETTLE_PRIVATE_KEY={pk_with_prefix}")
    print("  2. Fund the address above with:")
    print("     - USDC (Arc) for claim payouts")
    print("     - ARC (native) for gas (approve, depositEscrow, approveClaim)")
    print("  3. Optional: set AUTO_SETTLE_MAX_AMOUNT to cap the max USDC per auto-settle.")


if __name__ == "__main__":
    main()
