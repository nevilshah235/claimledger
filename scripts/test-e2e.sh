#!/bin/bash
# End-to-End API Test Script for ClaimLedger
# Tests the complete claim flow: Submit → Evaluate → Settle

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
CLAIMANT_ADDRESS="0xE2E2E2E2E2E2E2E2E2E2E2E2E2E2E2E2E2E2E2E2"
CLAIM_AMOUNT="750.00"

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     ClaimLedger E2E Test Suite             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Check if server is running
echo -e "${BLUE}[1/7] Checking API health...${NC}"
HEALTH=$(curl -s "$API_URL/health" 2>/dev/null || echo '{"status":"error"}')
if echo "$HEALTH" | grep -q '"healthy"'; then
    echo -e "${GREEN}✓ API is healthy${NC}"
else
    echo -e "${RED}✗ API is not running at $API_URL${NC}"
    echo -e "${YELLOW}Start the server with: make dev-backend${NC}"
    exit 1
fi

# Test 1: Create Claim
echo -e "\n${BLUE}[2/7] Creating test claim...${NC}"
CLAIM_RESULT=$(curl -s -X POST "$API_URL/claims" \
    -F "claimant_address=$CLAIMANT_ADDRESS" \
    -F "claim_amount=$CLAIM_AMOUNT")

CLAIM_ID=$(echo "$CLAIM_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('claim_id', ''))" 2>/dev/null)

if [ -z "$CLAIM_ID" ]; then
    echo -e "${RED}✗ Failed to create claim${NC}"
    echo "$CLAIM_RESULT"
    exit 1
fi
echo -e "${GREEN}✓ Claim created: $CLAIM_ID${NC}"

# Test 2: Get Claim Status
echo -e "\n${BLUE}[3/7] Verifying claim status...${NC}"
STATUS_RESULT=$(curl -s "$API_URL/claims/$CLAIM_ID")
STATUS=$(echo "$STATUS_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null)

if [ "$STATUS" = "SUBMITTED" ]; then
    echo -e "${GREEN}✓ Claim status is SUBMITTED${NC}"
else
    echo -e "${RED}✗ Unexpected status: $STATUS${NC}"
    exit 1
fi

# Test 3: x402 Verifier (without payment)
echo -e "\n${BLUE}[4/7] Testing x402 verifier (expect 402)...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/verifier/document" \
    -H "Content-Type: application/json" \
    -d "{\"claim_id\": \"$CLAIM_ID\", \"document_path\": \"/test/doc.pdf\"}")

if [ "$HTTP_CODE" = "402" ]; then
    echo -e "${GREEN}✓ Verifier correctly returned HTTP 402 Payment Required${NC}"
else
    echo -e "${RED}✗ Expected 402, got $HTTP_CODE${NC}"
    exit 1
fi

# Test 4: x402 Verifier (with payment)
echo -e "\n${BLUE}[5/7] Testing x402 verifier with payment...${NC}"
VERIFY_RESULT=$(curl -s -X POST "$API_URL/verifier/document" \
    -H "Content-Type: application/json" \
    -H "X-Payment-Receipt: test_receipt_e2e_123" \
    -d "{\"claim_id\": \"$CLAIM_ID\", \"document_path\": \"/test/doc.pdf\"}")

VALID=$(echo "$VERIFY_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('valid', False))" 2>/dev/null)

if [ "$VALID" = "True" ]; then
    echo -e "${GREEN}✓ Document verification successful${NC}"
else
    echo -e "${RED}✗ Document verification failed${NC}"
    echo "$VERIFY_RESULT"
    exit 1
fi

# Test 5: Agent Evaluation
echo -e "\n${BLUE}[6/7] Running AI agent evaluation...${NC}"
EVAL_RESULT=$(curl -s -X POST "$API_URL/agent/evaluate/$CLAIM_ID")
DECISION=$(echo "$EVAL_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('decision', ''))" 2>/dev/null)
CONFIDENCE=$(echo "$EVAL_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('confidence', 0))" 2>/dev/null)

if [ "$DECISION" = "APPROVED" ]; then
    echo -e "${GREEN}✓ Claim APPROVED with confidence: $CONFIDENCE${NC}"
else
    echo -e "${YELLOW}○ Claim decision: $DECISION (confidence: $CONFIDENCE)${NC}"
fi

# Test 6: Settlement (only if approved)
echo -e "\n${BLUE}[7/7] Testing blockchain settlement...${NC}"
if [ "$DECISION" = "APPROVED" ]; then
    SETTLE_RESULT=$(curl -s -X POST "$API_URL/blockchain/settle/$CLAIM_ID")
    TX_HASH=$(echo "$SETTLE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tx_hash', ''))" 2>/dev/null)
    
    if [ -n "$TX_HASH" ]; then
        echo -e "${GREEN}✓ Settlement successful${NC}"
        echo -e "  TX Hash: ${BLUE}$TX_HASH${NC}"
    else
        echo -e "${RED}✗ Settlement failed${NC}"
        echo "$SETTLE_RESULT"
        exit 1
    fi
else
    echo -e "${YELLOW}○ Skipping settlement (claim not approved)${NC}"
fi

# Final Status Check
echo -e "\n${BLUE}═══════════════════════════════════════════${NC}"
FINAL_STATUS=$(curl -s "$API_URL/claims/$CLAIM_ID")
echo -e "${GREEN}Final Claim Status:${NC}"
echo "$FINAL_STATUS" | python3 -m json.tool

echo -e "\n${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ✓ All E2E Tests Passed!                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
