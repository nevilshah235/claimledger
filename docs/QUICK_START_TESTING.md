# Quick Start: Testing ClaimLedger

## 🚀 Quick Start (5 Minutes)

### Step 1: Set Environment Variables (1 minute)

**Backend (`backend/.env`):**
```bash
# Minimum for testnet mode (no Circle needed!)
DATABASE_URL=sqlite:///./claimledger.db
JWT_SECRET_KEY=test-secret-key

# Optional: For real wallets
# CIRCLE_WALLETS_API_KEY=your_api_key_here
# CIRCLE_ENTITY_SECRET=your_entity_secret_here
```

**Frontend (`frontend/.env.local`):**
```bash
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Note:** You can test without Circle credentials! Mock wallets will be created automatically. See `docs/TESTNET_MODE.md` for details.

---

### Step 2: Start Backend (1 minute)

```bash
cd backend

# Install dependencies (if not done)
python -m pip install -e .

# Start server
python -m uvicorn src.main:app --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
🚀 Starting ClaimLedger API...
✅ Database tables created/verified
```

**Test it:**
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

---

### Step 3: Start Frontend (1 minute)

```bash
cd frontend

# Install dependencies (if not done)
npm install

# Start dev server
npm run dev
```

**Expected output:**
```
✓ Ready in 2.3s
○ Local:        http://localhost:3000
```

**Open in browser:**
- Visit: http://localhost:3000

---

## ✅ Testing Checklist

### Test 1: Backend API Health ✅

```bash
curl http://localhost:8000/health
```

**Expected:** `{"status":"healthy"}`

---

### Test 2: User Registration ✅

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123",
    "role": "claimant"
  }'
```

**Expected (testnet mode - mock wallet):**
```json
{
  "user_id": "...",
  "email": "test@example.com",
  "role": "claimant",
  "wallet_address": "0x1234...abcd",
  "access_token": "eyJ..."
}
```

**Expected (with Circle - real wallet):**
```json
{
  "user_id": "...",
  "email": "test@example.com",
  "role": "claimant",
  "wallet_address": "0x...",
  "access_token": "eyJ..."
}
```

---

### Test 3: User Login ✅

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123"
  }'
```

**Expected:**
```json
{
  "user_id": "...",
  "email": "test@example.com",
  "role": "claimant",
  "wallet_address": "0x...",
  "access_token": "eyJ..."
}
```

---

### Test 4: Get Current User ✅

```bash
# Use token from registration/login
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Expected:**
```json
{
  "user_id": "...",
  "email": "test@example.com",
  "role": "claimant",
  "wallet_address": "0x..."
}
```

---

### Test 5: Get Wallet Info ✅

```bash
curl http://localhost:8000/auth/wallet \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Expected:**
```json
{
  "wallet_address": "0x...",
  "circle_wallet_id": "...",
  "wallet_set_id": "...",
  "blockchain": "ARC",
  "balance": {...}
}
```

---

### Test 6: Frontend Build ✅

```bash
cd frontend
npm run build
```

**Expected:** `✓ Compiled successfully`

---

### Test 7: Frontend Authentication Flow (UI Test) ✅

1. **Open browser:** http://localhost:3000
2. **Click:** "Login as Claimant" button (top right)
3. **Register new account:**
   - Enter email and password
   - Click "Register"
4. **Expected:**
   - ✅ Wallet address appears automatically
   - ✅ User is logged in
   - ✅ Can navigate to claimant page

---

### Test 8: Submit Claim (End-to-End) ✅

1. **Navigate to:** http://localhost:3000/claimant
2. **Fill claim form:**
   - Enter claim amount (e.g., 500.00)
   - Upload evidence files (optional)
3. **Click:** "Submit Claim"
4. **Expected:**
   - ✅ Claim submitted successfully
   - ✅ Claim ID displayed
   - ✅ Status shows "SUBMITTED"

---

### Test 9: Insurer View ✅

1. **Register as insurer:**
   - Click "Login as Insurer"
   - Register with different email
2. **Navigate to:** http://localhost:3000/insurer
3. **Expected:**
   - ✅ See all claims (including claimant's claim)
   - ✅ Can view claim details
   - ✅ Can trigger settlement (if claim approved)

---

## 🐛 Troubleshooting

### Issue: "CIRCLE_ENTITY_SECRET not configured"

**Solution:**
- This is **expected** in testnet mode
- Mock wallets will be created automatically
- To use real wallets, see `docs/CIRCLE_ENTITY_SECRET_SETUP.md`

---

### Issue: "Email already registered"

**Solution:**
- User already exists
- Try logging in instead: `POST /auth/login`
- Or use a different email

---

### Issue: "Invalid authentication credentials"

**Solution:**
- Token expired or invalid
- Login again to get a new token
- Check token is included in `Authorization: Bearer <token>` header

---

### Issue: Backend returns 500 error

**Check:**
1. Backend logs for error details
2. Database is initialized
3. Dependencies installed: `python -m pip install -e .`

**Solution:**
```bash
# Restart backend with verbose logging
cd backend
python -m uvicorn src.main:app --reload --log-level debug
```

---

### Issue: Frontend build fails

**Check:**
1. Node.js version: `node --version` (should be 18+)
2. npm version: `npm --version`
3. Package.json dependencies installed

**Solution:**
```bash
cd frontend
rm -rf node_modules package-lock.json .next
npm install
npm run build
```

---

### Issue: CORS errors in browser

**Solution:**
- Backend CORS is configured for `http://localhost:3000`
- Check backend is running on port 8000
- Check frontend is running on port 3000
- Restart both servers if needed

---

## 📋 Manual Testing Scenarios

### Scenario 1: First-Time User Flow

1. ✅ User visits `/claimant`
2. ✅ Clicks "Login as Claimant"
3. ✅ Registers new account (email + password)
4. ✅ Wallet address appears automatically
5. ✅ Can submit claim with authenticated wallet

---

### Scenario 2: Returning User Flow

1. ✅ User visits `/claimant` (already registered)
2. ✅ Clicks "Login as Claimant"
3. ✅ Logs in with email + password
4. ✅ Wallet address automatically appears
5. ✅ Can immediately submit claim

---

### Scenario 3: Role Separation

1. ✅ Register as Claimant (wallet A)
2. ✅ Submit a claim
3. ✅ Register as Insurer (wallet B)
4. ✅ Navigate to `/insurer`
5. ✅ See all claims (including claimant's)
6. ✅ Can view and settle claims

---

### Scenario 4: Testnet Mode (No Circle)

1. ✅ Start backend without Circle credentials
2. ✅ Register user
3. ✅ Mock wallet created automatically
4. ✅ All features work for testing
5. ✅ Real wallets created when Circle is configured

---

## 🔍 Debugging Tips

### Backend Debugging

**Check logs:**
```bash
# Backend logs show:
# - User registration
# - Wallet creation (mock or real)
# - API calls to Circle (if configured)
# - Database operations
# - Error messages
```

**Test API directly:**
```bash
# Test registration
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","role":"claimant"}' | jq

# Test login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}' | jq

# Test get user (use token from login)
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN" | jq
```

---

### Frontend Debugging

**Browser DevTools:**
1. Open DevTools (F12)
2. **Console tab:** Check for errors
3. **Network tab:** Check API calls to backend
4. **Application tab:** Check localStorage for `auth_token`

**Check React state:**
- AuthModal component logs to console
- Check `auth_token` in localStorage
- Verify API calls include `Authorization` header

---

### Database Debugging

**Check SQLite database:**
```bash
cd backend
sqlite3 claimledger.db

# List tables
.tables

# Check users
SELECT id, email, role FROM users;

# Check user_wallets
SELECT * FROM user_wallets;

# Check claims
SELECT id, claimant_address, status FROM claims;

# Exit
.quit
```

---

## 📊 Success Criteria

### ✅ All Tests Passing

- [ ] Backend health check returns 200
- [ ] User registration works (creates wallet)
- [ ] User login works
- [ ] JWT token validation works
- [ ] Frontend builds without errors
- [ ] AuthModal component works
- [ ] Wallet address displays after registration
- [ ] Claim submission uses authenticated user's wallet
- [ ] Insurer can view all claims
- [ ] Role-based access control works
- [ ] Testnet mode works without Circle credentials

---

## 🎯 Next Steps After Testing

Once basic auth and wallet flow works:

1. **Test Claim Submission:**
   - Submit a claim as authenticated claimant
   - Verify `claimant_address` is set from user's wallet

2. **Test Agent Evaluation:**
   - Trigger agent evaluation
   - Verify x402 payments work (if Gateway configured)

3. **Test Settlement:**
   - Connect as insurer
   - Approve a claim
   - Trigger settlement
   - Verify transaction on Arc

---

## 📚 Additional Resources

- **Environment Setup:** `docs/ENVIRONMENT_VARIABLES.md`
- **Backend Auth Testing:** `docs/BACKEND_AUTH_TESTING.md`
- **Testnet Mode:** `docs/TESTNET_MODE.md`
- **Entity Secret Setup:** `docs/CIRCLE_ENTITY_SECRET_SETUP.md`

---

## 💡 Quick Commands Reference

```bash
# Backend
cd backend
python -m uvicorn src.main:app --reload

# Frontend
cd frontend
npm run dev

# Test backend
curl http://localhost:8000/health

# Test registration
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","role":"claimant"}'

# Test login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Build frontend
cd frontend && npm run build

# Check database
cd backend && sqlite3 claimledger.db ".tables"
```

---

**Ready to test?** Start with Step 1 above! 🚀
