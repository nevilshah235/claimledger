#!/bin/bash
# Quick Start Testing Script
# Tests all endpoints and functionality from QUICK_START_TESTING.md

# Don't exit on error - we want to run all tests
set +e

BASE_URL="${BASE_URL:-http://localhost:8000}"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Test counter
test_count=0

# Helper functions
pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
    ((PASSED++))
    ((test_count++))
}

fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    ((FAILED++))
    ((test_count++))
}

info() {
    echo -e "${YELLOW}ℹ️  INFO${NC}: $1"
}

# Check if server is running
check_server() {
    info "Checking if backend server is running at $BASE_URL..."
    if curl -s -f "$BASE_URL/health" > /dev/null 2>&1; then
        pass "Backend server is running"
        return 0
    else
        fail "Backend server is not running at $BASE_URL"
        echo "   Please start the backend: cd backend && python -m uvicorn src.main:app --reload"
        return 1
    fi
}

# Test 1: Backend API Health
test_health() {
    echo ""
    echo "=== Test 1: Backend API Health ==="
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/health")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        if echo "$body" | grep -q "healthy"; then
            pass "Health endpoint returns 200 with 'healthy' status"
        else
            fail "Health endpoint returns 200 but missing 'healthy' status"
        fi
    else
        fail "Health endpoint returned $http_code instead of 200"
    fi
}

# Test 2: User Registration
test_registration() {
    echo ""
    echo "=== Test 2: User Registration ==="
    TEST_EMAIL="test_$(date +%s)@example.com"
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/auth/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"email\": \"$TEST_EMAIL\",
            \"password\": \"test123\",
            \"role\": \"claimant\"
        }")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "201" ]; then
        if echo "$body" | grep -q "user_id" && echo "$body" | grep -q "wallet_address" && echo "$body" | grep -q "access_token"; then
            pass "User registration successful"
            # Extract token for later tests
            export TEST_TOKEN=$(echo "$body" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
            export TEST_USER_ID=$(echo "$body" | grep -o '"user_id":"[^"]*' | cut -d'"' -f4)
            export TEST_EMAIL="$TEST_EMAIL"
        else
            fail "Registration returned 201 but missing required fields"
        fi
    else
        fail "Registration returned $http_code instead of 201"
        echo "   Response: $body"
    fi
}

# Test 3: User Login
test_login() {
    echo ""
    echo "=== Test 3: User Login ==="
    
    if [ -z "$TEST_EMAIL" ]; then
        fail "Cannot test login - no test user created"
        return
    fi
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/auth/login" \
        -H "Content-Type: application/json" \
        -d "{
            \"email\": \"$TEST_EMAIL\",
            \"password\": \"test123\"
        }")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        if echo "$body" | grep -q "access_token"; then
            pass "User login successful"
            export LOGIN_TOKEN=$(echo "$body" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
        else
            fail "Login returned 200 but missing access_token"
        fi
    else
        fail "Login returned $http_code instead of 200"
        echo "   Response: $body"
    fi
}

# Test 4: Get Current User
test_get_current_user() {
    echo ""
    echo "=== Test 4: Get Current User ==="
    
    if [ -z "$TEST_TOKEN" ]; then
        fail "Cannot test get current user - no token available"
        return
    fi
    
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/auth/me" \
        -H "Authorization: Bearer $TEST_TOKEN")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        if echo "$body" | grep -q "user_id" && echo "$body" | grep -q "email"; then
            pass "Get current user successful"
        else
            fail "Get current user returned 200 but missing required fields"
        fi
    else
        fail "Get current user returned $http_code instead of 200"
        echo "   Response: $body"
    fi
}

# Test 5: Get Wallet Info
test_get_wallet() {
    echo ""
    echo "=== Test 5: Get Wallet Info ==="
    
    if [ -z "$TEST_TOKEN" ]; then
        fail "Cannot test get wallet - no token available"
        return
    fi
    
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/auth/wallet" \
        -H "Authorization: Bearer $TEST_TOKEN")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        if echo "$body" | grep -q "wallet_address"; then
            pass "Get wallet info successful"
        else
            fail "Get wallet returned 200 but missing wallet_address"
        fi
    else
        fail "Get wallet returned $http_code instead of 200"
        echo "   Response: $body"
    fi
}

# Test 6: Demo User Login (Admin)
test_demo_admin_login() {
    echo ""
    echo "=== Test 6: Demo Admin User Login ==="
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/auth/login" \
        -H "Content-Type: application/json" \
        -d '{
            "email": "admin@uclaim.com",
            "password": "AdminDemo123!"
        }')
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        if echo "$body" | grep -q "access_token"; then
            pass "Demo admin user login successful"
            export ADMIN_TOKEN=$(echo "$body" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
        else
            fail "Demo admin login returned 200 but missing access_token"
        fi
    else
        if [ "$http_code" = "401" ]; then
            info "Demo admin user may not exist yet (will be created on first DB init)"
        else
            fail "Demo admin login returned $http_code instead of 200"
        fi
    fi
}

# Test 7: Demo User Login (Claimant)
test_demo_claimant_login() {
    echo ""
    echo "=== Test 7: Demo Claimant User Login ==="
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/auth/login" \
        -H "Content-Type: application/json" \
        -d '{
            "email": "claimant@uclaim.com",
            "password": "ClaimantDemo123!"
        }')
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        if echo "$body" | grep -q "access_token"; then
            pass "Demo claimant user login successful"
            export CLAIMANT_TOKEN=$(echo "$body" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
        else
            fail "Demo claimant login returned 200 but missing access_token"
        fi
    else
        if [ "$http_code" = "401" ]; then
            info "Demo claimant user may not exist yet (will be created on first DB init)"
        else
            fail "Demo claimant login returned $http_code instead of 200"
        fi
    fi
}

# Test 8: Invalid Login
test_invalid_login() {
    echo ""
    echo "=== Test 8: Invalid Login (Error Handling) ==="
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/auth/login" \
        -H "Content-Type: application/json" \
        -d '{
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }')
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "401" ]; then
        pass "Invalid login correctly returns 401"
    else
        fail "Invalid login returned $http_code instead of 401"
    fi
}

# Test 9: Duplicate Registration
test_duplicate_registration() {
    echo ""
    echo "=== Test 9: Duplicate Registration (Error Handling) ==="
    
    if [ -z "$TEST_EMAIL" ]; then
        info "Skipping duplicate registration test - no test user created"
        return
    fi
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/auth/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"email\": \"$TEST_EMAIL\",
            \"password\": \"test123\",
            \"role\": \"claimant\"
        }")
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "400" ]; then
        pass "Duplicate registration correctly returns 400"
    else
        fail "Duplicate registration returned $http_code instead of 400"
    fi
}

# Test 10: Unauthorized Access
test_unauthorized_access() {
    echo ""
    echo "=== Test 10: Unauthorized Access (Error Handling) ==="
    
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/auth/me")
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "401" ] || [ "$http_code" = "403" ]; then
        pass "Unauthorized access correctly returns $http_code"
    else
        fail "Unauthorized access returned $http_code instead of 401/403"
    fi
}

# Test 11: Wallet Address Uniqueness
test_wallet_address_uniqueness() {
    echo ""
    echo "=== Test 11: Wallet Address Uniqueness ==="
    
    # Get admin wallet
    admin_response=$(curl -s -X POST "$BASE_URL/auth/login" \
        -H "Content-Type: application/json" \
        -d '{
            "email": "admin@uclaim.com",
            "password": "AdminDemo123!"
        }')
    
    admin_wallet=$(echo "$admin_response" | grep -o '"wallet_address":"[^"]*' | cut -d'"' -f4)
    
    # Get claimant wallet
    claimant_response=$(curl -s -X POST "$BASE_URL/auth/login" \
        -H "Content-Type: application/json" \
        -d '{
            "email": "claimant@uclaim.com",
            "password": "ClaimantDemo123!"
        }')
    
    claimant_wallet=$(echo "$claimant_response" | grep -o '"wallet_address":"[^"]*' | cut -d'"' -f4)
    
    if [ -z "$admin_wallet" ] || [ -z "$claimant_wallet" ]; then
        if [ -z "$admin_wallet" ] && [ -z "$claimant_wallet" ]; then
            info "Both wallets are missing (Circle credentials may not be configured)"
        else
            fail "One wallet is missing (admin: ${admin_wallet:-null}, claimant: ${claimant_wallet:-null})"
        fi
        return
    fi
    
    if [ "$admin_wallet" = "$claimant_wallet" ]; then
        fail "Wallet addresses are the same: $admin_wallet"
        echo "   This indicates wallets are not being created uniquely per user"
    else
        pass "Wallet addresses are different (admin: ${admin_wallet:0:10}..., claimant: ${claimant_wallet:0:10}...)"
    fi
}

# Main execution
main() {
    echo "=========================================="
    echo "  ClaimLedger Quick Start Test Suite"
    echo "=========================================="
    echo ""
    echo "Testing against: $BASE_URL"
    echo ""
    
    # Check if server is running
    if ! check_server; then
        echo ""
        echo "=========================================="
        echo "  Test Summary"
        echo "=========================================="
        echo -e "${RED}❌ Tests cannot run - server not available${NC}"
        exit 1
    fi
    
    # Run all tests
    test_health
    test_registration
    test_login
    test_get_current_user
    test_get_wallet
    test_demo_admin_login
    test_demo_claimant_login
    test_invalid_login
    test_duplicate_registration
    test_unauthorized_access
    test_wallet_address_uniqueness
    
    # Print summary
    echo ""
    echo "=========================================="
    echo "  Test Summary"
    echo "=========================================="
    echo -e "Total Tests: $test_count"
    echo -e "${GREEN}Passed: $PASSED${NC}"
    echo -e "${RED}Failed: $FAILED${NC}"
    echo ""
    
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}✅ All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}❌ Some tests failed${NC}"
        exit 1
    fi
}

# Run main function
main
