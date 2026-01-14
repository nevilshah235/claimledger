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

echo -e "${YELLOW}Step 3: Installing Cython < 3.0 and PyYAML...${NC}"
pip3 install --upgrade pip setuptools wheel
pip3 install "cython<3.0.0" wheel
pip3 install "pyyaml==5.4.1" --no-build-isolation
echo -e "${GREEN}✅ Cython and PyYAML installed${NC}"
echo ""

echo -e "${YELLOW}Step 4: Installing compatible markupsafe for Rye...${NC}"
pip3 install "markupsafe<2.1.0"
echo -e "${GREEN}✅ markupsafe installed${NC}"
echo ""

echo -e "${YELLOW}Step 5: Installing Rye...${NC}"
pip3 install rye
echo -e "${GREEN}✅ Rye installed${NC}"
echo ""

echo -e "${YELLOW}Step 6: Installing project dependencies with Rye...${NC}"
cd backend
rye sync
echo -e "${GREEN}✅ Dependencies synced${NC}"
echo ""

echo -e "${YELLOW}Step 7: Running tests...${NC}"
rye run pytest || {
    echo -e "${RED}❌ Tests failed${NC}"
    exit 1
}
echo -e "${GREEN}✅ Tests passed${NC}"
echo ""

echo -e "${GREEN}✅ All CI steps completed successfully!${NC}"
echo ""
