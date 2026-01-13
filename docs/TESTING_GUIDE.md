# Testing ClaimEscrow Contract - Step by Step 🧪

## Quick Test with Remix IDE (5 Minutes!) ⚡

If you want to test quickly without installation:

### Step 1: Open Remix
👉 **Go to:** https://remix.ethereum.org

### Step 2: Create Files

**File 1: MockUSDC.sol**
1. Click **"File Explorer"** (left sidebar)
2. Click **"Create new file"**
3. Name: `MockUSDC.sol`
4. Paste the MockUSDC code (see below in detailed section)

**File 2: ClaimEscrow.sol**
1. Create new file: `ClaimEscrow.sol`
2. Copy from: `contracts/src/ClaimEscrow.sol`

### Step 3: Compile
1. Click **"Solidity Compiler"** (left sidebar)
2. Version: **0.8.20**
3. Click **"Compile ClaimEscrow.sol"**
4. ✅ Green checkmark = Success!

### Step 4: Deploy
1. Click **"Deploy & Run Transactions"** (left sidebar)
2. Environment: **"Remix VM (Berlin)"**
3. **Deploy MockUSDC first:**
   - Select: `MockUSDC`
   - Click **"Deploy"**
   - Copy the address (e.g., `0x5FbDB...`)
4. **Deploy ClaimEscrow:**
   - Select: `ClaimEscrow`
   - Enter MockUSDC address in deploy field
   - Click **"Deploy"**

### Step 5: Test!

**Test 1: Deposit**
- Function: `depositEscrow`
- claimId: `1`
- amount: `1000000` (1 USDC)
- Click **"depositEscrow"**
- ✅ Should work!

**Test 2: Check Balance**
- Function: `getEscrowBalance`
- claimId: `1`
- Click **"call"**
- ✅ Should return: `1000000`

**Test 3: Approve**
- Function: `approveClaim`
- claimId: `1`
- amount: `1000000`
- recipient: `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb`
- Click **"approveClaim"**
- ✅ Should work!

**Done! Your contract works!** 🎉

**For detailed instructions and Foundry testing, continue reading below.**

---

## Quick Decision: Which Method?

**Option A: Remix IDE (Web-Based)** ⭐ Recommended for Beginners
- ✅ No installation needed
- ✅ Visual interface
- ✅ Works in browser
- ✅ Easy to use

**Option B: Foundry (Command-Line)**
- ✅ More powerful
- ✅ Better for CI/CD
- ✅ Faster compilation
- ❌ Needs installation

---

## Option A: Test with Remix IDE (Easiest!)

### Step 1: Open Remix

1. Go to: **https://remix.ethereum.org**
2. Wait for it to load (no signup needed!)

### Step 2: Create Contract Files

1. **Left sidebar** → Click **"File Explorer"**
2. **Create new file** → Name: `ClaimEscrow.sol`
3. **Paste your contract code** (from `contracts/src/ClaimEscrow.sol`)
4. **Create another file** → Name: `MockUSDC.sol`
5. **Paste mock USDC code** (see below)

**MockUSDC.sol** (for testing):
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MockUSDC {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    
    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }
    
    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(balanceOf[from] >= amount, "Insufficient balance");
        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        allowance[from][msg.sender] -= amount;
        return true;
    }
    
    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }
    
    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
    }
}
```

### Step 3: Compile

1. **Left sidebar** → Click **"Solidity Compiler"**
2. **Compiler version:** Select **0.8.20**
3. **Click "Compile ClaimEscrow.sol"**
4. ✅ **Green checkmark** = Success!

### Step 4: Deploy for Testing

1. **Left sidebar** → Click **"Deploy & Run Transactions"**
2. **Environment:** Select **"Remix VM (Berlin)"** (for local testing)
3. **Deploy MockUSDC first:**
   - Select contract: **MockUSDC**
   - Click **"Deploy"**
   - Copy the deployed address
4. **Deploy ClaimEscrow:**
   - Select contract: **ClaimEscrow**
   - In **"Deploy"** section, enter MockUSDC address
   - Click **"Deploy"**

### Step 5: Test Functions

**Test 1: Deposit Escrow**
1. Under **"Deployed Contracts"**, expand **ClaimEscrow**
2. Find **"depositEscrow"** function
3. Enter:
   - `claimId`: `1`
   - `amount`: `1000000` (1 USDC with 6 decimals)
4. Click **"depositEscrow"**
5. ✅ Should succeed!

**Test 2: Check Balance**
1. Find **"getEscrowBalance"** function
2. Enter: `1` (claimId)
3. Click **"call"**
4. ✅ Should return: `1000000`

**Test 3: Approve Claim**
1. Find **"approveClaim"** function
2. Enter:
   - `claimId`: `1`
   - `amount`: `1000000`
   - `recipient`: `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb` (or any address)
3. Click **"approveClaim"**
4. ✅ Should succeed!

**Test 4: Check if Settled**
1. Find **"isSettled"** function
2. Enter: `1` (claimId)
3. Click **"call"**
4. ✅ Should return: `true`

### Step 6: Test Error Cases

**Test: Try to settle twice**
1. Try calling **"approveClaim"** again with same claimId
2. ✅ Should fail with error!

**Test: Try to settle more than escrow**
1. Deploy new contract
2. Deposit: `1000000` (1 USDC)
3. Try to approve: `2000000` (2 USDC)
4. ✅ Should fail with "Insufficient escrow balance"!

---

## Option B: Test with Foundry (Command-Line)

### Step 1: Install Foundry

```bash
# Install Foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Verify installation
forge --version
cast --version
```

### Step 2: Install Dependencies

```bash
cd /Users/nevil/Documents/Projects/agenticai-arc/contracts

# Install forge-std library
forge install foundry-rs/forge-std --no-commit
```

### Step 3: Build the Contract

```bash
# Build (compile) the contract
forge build
```

**Expected output:**
```
[⠊] Compiling...
[⠊] Compiling 1 files with 0.8.20
[⠊] Solc 0.8.20 finished in 123.45ms
Compiler run successful!
```

### Step 4: Run Tests

```bash
# Run all tests
forge test
```

**Expected output:**
```
[PASS] testDepositEscrow()
[PASS] testApproveClaim()
[PASS] testCannotSettleTwice()
[PASS] testCannotSettleMoreThanEscrow()

Test result: ok. 4 passed; 0 failed; finished in 123.45ms
```

### Step 5: Run Tests with Verbose Output

```bash
# See detailed test output
forge test -vvv
```

**This shows:**
- Function calls
- Return values
- Gas usage
- Console logs

---

## Understanding Test Results

### ✅ Test Passes
```
[PASS] testDepositEscrow()
```
**Meaning:** The function works correctly!

### ❌ Test Fails
```
[FAIL. Reason: Insufficient escrow balance] testCannotSettleMoreThanEscrow()
```
**Meaning:** Either:
- Test is wrong (fix the test)
- Contract has a bug (fix the contract)

### 🔍 Verbose Output
```
[PASS] testDepositEscrow()
Traces:
  [12345] ClaimEscrowTest::testDepositEscrow()
    ├─ [10000] ClaimEscrow::depositEscrow(1, 1000000)
    │   └─ [5000] MockUSDC::transferFrom(...)
    └─ ← ()
```
**Meaning:** Shows step-by-step what happened

---

## What Each Test Does

### testDepositEscrow()
- **Tests:** Can deposit USDC into escrow
- **Checks:** Balance increases correctly
- **Expected:** ✅ Pass

### testApproveClaim()
- **Tests:** Can approve and settle a claim
- **Checks:** USDC transferred to recipient
- **Expected:** ✅ Pass

### testCannotSettleTwice()
- **Tests:** Can't settle same claim twice
- **Checks:** Error when trying to settle again
- **Expected:** ✅ Pass (should fail with error)

### testCannotSettleMoreThanEscrow()
- **Tests:** Can't settle more than what's in escrow
- **Checks:** Error when amount > escrow balance
- **Expected:** ✅ Pass (should fail with error)

---

## Troubleshooting

### Error: "forge: command not found"
**Problem:** Foundry not installed
**Solution:** Install Foundry (see Step 1 above)

### Error: "forge-std not found"
**Problem:** Dependencies not installed
**Solution:** Run `forge install foundry-rs/forge-std --no-commit`

### Error: "Compilation failed"
**Problem:** Contract has syntax errors
**Solution:** Check contract code, fix errors

### Error: "Test failed"
**Problem:** Contract logic is wrong or test is wrong
**Solution:** 
1. Check test expectations
2. Check contract logic
3. Run with `-vvv` to see details

---

## Next Steps After Tests Pass

Once all tests pass ✅:

1. **Deploy to Arc Testnet** (Step 9 in DEPLOYMENT_GUIDE.md)
2. **Test on real testnet** (Step 12 in DEPLOYMENT_GUIDE.md)
3. **Integrate with backend** (Phase 2)

---

## Quick Reference

### Remix IDE (Web-Based)
- URL: https://remix.ethereum.org
- No installation needed
- Visual interface
- Best for: Quick testing, beginners

### Foundry (Command-Line)
- Install: `curl -L https://foundry.paradigm.xyz | bash && foundryup`
- Build: `forge build`
- Test: `forge test`
- Best for: Advanced testing, CI/CD

---

## Ready to Test?

**Choose your method:**
- **Beginners:** Use Remix IDE (Option A)
- **Advanced:** Use Foundry (Option B)

Let me know which you prefer and I'll guide you through it! 🚀
