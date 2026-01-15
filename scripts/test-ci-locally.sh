#!/bin/bash
# Script to test CI steps locally before pushing
# This simulates the GitHub Actions CI workflow

set -e  # Exit on error

echo "🧪 Testing CI steps locally..."
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -d "backend" ]; then
    echo -e "${RED}❌ Error: Must run from project root${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Checking Python version...${NC}"
python3 --version
echo ""

echo -e "${YELLOW}Step 2: Installing build dependencies (simulated - skipping on macOS)...${NC}"
# On macOS, these are usually already available or need different commands
# We'll skip the apt-get commands but note them
echo "  Note: On CI, this would run: sudo apt-get update && sudo apt-get install -y build-essential libssl-dev libffi-dev python3-dev"
echo ""

echo -e "${YELLOW}Step 3: Installing uv...${NC}"
pip3 install uv || curl -LsSf https://astral.sh/uv/install.sh | sh
echo -e "${GREEN}✅ uv installed${NC}"
echo ""

echo -e "${YELLOW}Step 4: Installing project dependencies with uv...${NC}"
cd backend
uv pip install -e ".[dev]"
echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

echo -e "${YELLOW}Step 5: Running tests...${NC}"
uv run pytest || {
    echo -e "${RED}❌ Tests failed${NC}"
    exit 1
}
echo -e "${GREEN}✅ Tests passed${NC}"
echo ""

echo -e "${GREEN}✅ All CI steps completed successfully!${NC}"
echo ""
