#!/bin/bash
# Load testnet environment variables from .env.testnet
# Usage: source scripts/load-testnet-env.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env.testnet"

if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  Warning: .env.testnet not found"
    echo "   Create it from .env.testnet.example"
    echo "   cp .env.testnet.example .env.testnet"
    return 1
fi

# Load environment variables
export $(grep -v '^#' "$ENV_FILE" | xargs)

echo "✅ Loaded testnet environment variables from .env.testnet"
echo "   ARC_RPC_URL: $ARC_RPC_URL"
echo "   USDC_ADDRESS: $USDC_ADDRESS"
echo "   DEPLOYER_ADDRESS: ${DEPLOYER_ADDRESS:0:10}..." # Show only first 10 chars
