#!/bin/bash
# Quick script to test ClaimEscrow contract

set -e  # Exit on error

echo "🧪 Testing ClaimEscrow Contract"
echo ""

# Check if Foundry is installed
if ! command -v forge &> /dev/null; then
    echo "❌ Foundry is not installed"
    echo ""
    echo "Installing Foundry..."
    curl -L https://foundry.paradigm.xyz | bash
    foundryup
    echo ""
    echo "✅ Foundry installed!"
    echo ""
fi

cd "$(dirname "$0")"

echo "📦 Step 1: Installing dependencies..."
forge install foundry-rs/forge-std --no-commit || echo "Dependencies already installed"
echo ""

echo "🔨 Step 2: Building contract..."
forge build
echo ""

echo "🧪 Step 3: Running tests..."
forge test -vv
echo ""

echo "✅ Testing complete!"
echo ""
echo "If all tests passed, you're ready to deploy! 🚀"
