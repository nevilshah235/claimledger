#!/bin/bash

# End-to-End Test Script for Agentic Flow
# This script tests the complete agentic evaluation workflow

set -e

echo "=========================================="
echo "E2E Agentic Flow Test"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKEND_DIR="backend"
FRONTEND_DIR="frontend"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
MAX_WAIT_TIME=60  # seconds

# Function to check if backend is running
check_backend() {
    echo -e "${YELLOW}Checking if backend is running...${NC}"
    if curl -s -f "${BACKEND_URL}/health" > /dev/null; then
        echo -e "${GREEN}✓ Backend is running${NC}"
        return 0
    else
        echo -e "${RED}✗ Backend is not running at ${BACKEND_URL}${NC}"
        echo "Please start the backend server first:"
        echo "  cd ${BACKEND_DIR} && uv run uvicorn src.main:app --reload"
        return 1
    fi
}

# Function to wait for evaluation to complete
wait_for_evaluation() {
    local claim_id=$1
    local elapsed=0
    
    echo -e "${YELLOW}Waiting for evaluation to complete...${NC}"
    
    while [ $elapsed -lt $MAX_WAIT_TIME ]; do
        status=$(curl -s "${BACKEND_URL}/agent/status/${claim_id}" | jq -r '.status' 2>/dev/null || echo "EVALUATING")
        
        if [ "$status" != "EVALUATING" ]; then
            echo -e "${GREEN}✓ Evaluation completed with status: ${status}${NC}"
            return 0
        fi
        
        sleep 2
        elapsed=$((elapsed + 2))
        echo -n "."
    done
    
    echo -e "\n${RED}✗ Evaluation timed out after ${MAX_WAIT_TIME} seconds${NC}"
    return 1
}

# Function to create a test claim
create_test_claim() {
    echo -e "${YELLOW}Creating test claim...${NC}"
    
    # Create a simple test file
    mkdir -p /tmp/test_claim
    echo "Test invoice content" > /tmp/test_claim/invoice.txt
    
    # Note: This is a simplified version. In a real scenario, you'd need to:
    # 1. Authenticate first
    # 2. Upload actual files
    # For now, we'll use the API directly if available
    
    echo -e "${YELLOW}Note: Full claim creation requires authentication and file uploads${NC}"
    echo "This script tests the evaluation endpoints assuming a claim exists"
}

# Function to test agent results endpoint
test_agent_results() {
    local claim_id=$1
    
    echo -e "${YELLOW}Testing GET /agent/results/${claim_id}...${NC}"
    
    response=$(curl -s -w "\n%{http_code}" "${BACKEND_URL}/agent/results/${claim_id}")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Agent results endpoint returned 200${NC}"
        echo "$body" | jq '.' > /dev/null 2>&1 && echo -e "${GREEN}✓ Response is valid JSON${NC}" || echo -e "${YELLOW}⚠ Response is not valid JSON${NC}"
        return 0
    else
        echo -e "${RED}✗ Agent results endpoint returned ${http_code}${NC}"
        return 1
    fi
}

# Function to test evaluation status endpoint
test_evaluation_status() {
    local claim_id=$1
    
    echo -e "${YELLOW}Testing GET /agent/status/${claim_id}...${NC}"
    
    response=$(curl -s -w "\n%{http_code}" "${BACKEND_URL}/agent/status/${claim_id}")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Evaluation status endpoint returned 200${NC}"
        
        # Check required fields
        if echo "$body" | jq -e '.claim_id' > /dev/null 2>&1 && \
           echo "$body" | jq -e '.status' > /dev/null 2>&1 && \
           echo "$body" | jq -e '.completed_agents' > /dev/null 2>&1 && \
           echo "$body" | jq -e '.pending_agents' > /dev/null 2>&1 && \
           echo "$body" | jq -e '.progress_percentage' > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Response contains all required fields${NC}"
            return 0
        else
            echo -e "${RED}✗ Response missing required fields${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ Evaluation status endpoint returned ${http_code}${NC}"
        return 1
    fi
}

# Function to test evaluation endpoint
test_evaluation() {
    local claim_id=$1
    
    echo -e "${YELLOW}Testing POST /agent/evaluate/${claim_id}...${NC}"
    
    response=$(curl -s -w "\n%{http_code}" -X POST "${BACKEND_URL}/agent/evaluate/${claim_id}")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Evaluation endpoint returned 200${NC}"
        
        # Check for new fields in response
        if echo "$body" | jq -e '.agent_results' > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Response includes agent_results field${NC}"
        else
            echo -e "${YELLOW}⚠ Response does not include agent_results field${NC}"
        fi
        
        if echo "$body" | jq -e '.tool_calls' > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Response includes tool_calls field${NC}"
        else
            echo -e "${YELLOW}⚠ Response does not include tool_calls field (may be null)${NC}"
        fi
        
        return 0
    else
        echo -e "${RED}✗ Evaluation endpoint returned ${http_code}${NC}"
        echo "$body"
        return 1
    fi
}

# Function to verify agent results in database
verify_agent_results() {
    local claim_id=$1
    
    echo -e "${YELLOW}Verifying agent results in database...${NC}"
    
    # This would require database access. For now, we'll check via API
    results=$(curl -s "${BACKEND_URL}/agent/results/${claim_id}")
    
    if echo "$results" | jq -e '.agent_results | length > 0' > /dev/null 2>&1; then
        count=$(echo "$results" | jq '.agent_results | length')
        echo -e "${GREEN}✓ Found ${count} agent result(s)${NC}"
        return 0
    else
        echo -e "${RED}✗ No agent results found${NC}"
        return 1
    fi
}

# Main test flow
main() {
    echo ""
    
    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}✗ jq is required but not installed${NC}"
        echo "Install with: brew install jq (macOS) or apt-get install jq (Linux)"
        exit 1
    fi
    
    # Check if curl is installed
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}✗ curl is required but not installed${NC}"
        exit 1
    fi
    
    # Check backend
    if ! check_backend; then
        exit 1
    fi
    
    echo ""
    echo -e "${YELLOW}=========================================="
    echo "Test Flow"
    echo "==========================================${NC}"
    echo ""
    
    # For this script, we'll use a test claim ID if provided, or prompt for one
    if [ -z "$1" ]; then
        echo -e "${YELLOW}Usage: $0 <claim_id>${NC}"
        echo "Or set CLAIM_ID environment variable"
        echo ""
        echo "To test with a real claim:"
        echo "1. Create a claim via the API or UI"
        echo "2. Run: $0 <claim_id>"
        exit 1
    fi
    
    CLAIM_ID=$1
    
    echo -e "${YELLOW}Using claim ID: ${CLAIM_ID}${NC}"
    echo ""
    
    # Test evaluation status endpoint
    echo "Step 1: Test evaluation status endpoint"
    if ! test_evaluation_status "$CLAIM_ID"; then
        echo -e "${RED}Failed at step 1${NC}"
        exit 1
    fi
    echo ""
    
    # Test agent results endpoint (before evaluation)
    echo "Step 2: Test agent results endpoint (before evaluation)"
    test_agent_results "$CLAIM_ID"
    echo ""
    
    # Test evaluation endpoint
    echo "Step 3: Trigger evaluation"
    if ! test_evaluation "$CLAIM_ID"; then
        echo -e "${RED}Failed at step 3${NC}"
        exit 1
    fi
    echo ""
    
    # Wait for evaluation to complete
    echo "Step 4: Wait for evaluation to complete"
    if ! wait_for_evaluation "$CLAIM_ID"; then
        echo -e "${RED}Failed at step 4${NC}"
        exit 1
    fi
    echo ""
    
    # Test agent results endpoint (after evaluation)
    echo "Step 5: Test agent results endpoint (after evaluation)"
    if ! test_agent_results "$CLAIM_ID"; then
        echo -e "${RED}Failed at step 5${NC}"
        exit 1
    fi
    echo ""
    
    # Verify agent results
    echo "Step 6: Verify agent results"
    if ! verify_agent_results "$CLAIM_ID"; then
        echo -e "${RED}Failed at step 6${NC}"
        exit 1
    fi
    echo ""
    
    echo -e "${GREEN}=========================================="
    echo "✓ All E2E tests passed!"
    echo "==========================================${NC}"
    echo ""
}

# Run main function
main "$@"
