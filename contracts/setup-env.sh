#!/bin/bash
# Setup script for Arc testnet deployment

echo "🚀 Setting up Arc testnet deployment environment..."
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cat > .env << EOF
# Arc Testnet Configuration
# WARNING: Never commit this file to git!

# Your deployer wallet private key (for testnet only!)
# Generate with: cast wallet new
PRIVATE_KEY=0x...

# Arc Testnet USDC Contract Address
# Official address from: https://docs.arc.network/arc/references/contract-addresses
# USDC ERC-20 interface uses 6 decimals
USDC_ADDRESS=0x3600000000000000000000000000000000000000

# Arc Testnet RPC URL
ARC_RPC_URL=https://arc-testnet.rpc.circle.com

# Arc Testnet Chain ID
ARC_CHAIN_ID=11124
EOF
    echo "✅ Created .env file"
    echo "⚠️  Please edit .env and add your PRIVATE_KEY"
else
    echo "ℹ️  .env file already exists"
fi

echo ""
echo "📋 Next steps:"
echo "1. Edit .env and add your PRIVATE_KEY"
echo "2. Run: forge install foundry-rs/forge-std --no-commit"
echo "3. Run: forge build"
echo "4. Run: forge test"
echo "5. Run: source .env && forge script script/Deploy.s.sol:DeployClaimEscrow --rpc-url \$ARC_RPC_URL --private-key \$PRIVATE_KEY --broadcast --slow"
echo ""
