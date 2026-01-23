/**
 * Frontend Wallet Address Test Script
 * 
 * Run this in the browser console (F12) on http://localhost:3000
 * Tests that different users have different wallet addresses
 */

(async function testWalletAddresses() {
  const API_URL = 'http://localhost:8000';
  
  console.log('🧪 Testing Wallet Address Uniqueness...\n');
  console.log('='.repeat(50));
  
  try {
    // Test 1: Login as Admin
    console.log('\n1️⃣ Testing Admin User...');
    const adminRes = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        email: 'admin@uclaim.com', 
        password: 'AdminDemo123!' 
      })
    });
    
    if (!adminRes.ok) {
      const error = await adminRes.json();
      throw new Error(`Admin login failed: ${error.detail || adminRes.statusText}`);
    }
    
    const admin = await adminRes.json();
    const adminWallet = admin.wallet_address;
    const adminToken = admin.access_token;
    
    console.log('✅ Admin login successful');
    console.log('   Email:', admin.email);
    console.log('   Role:', admin.role);
    console.log('   Wallet:', adminWallet || '❌ Missing');
    
    // Get wallet info via API
    let adminWalletInfo = null;
    if (adminToken) {
      try {
        const walletRes = await fetch(`${API_URL}/auth/wallet`, {
          headers: { 'Authorization': `Bearer ${adminToken}` }
        });
        if (walletRes.ok) {
          adminWalletInfo = await walletRes.json();
          console.log('   Wallet Info:', {
            address: adminWalletInfo.wallet_address,
            blockchain: adminWalletInfo.blockchain,
            circle_wallet_id: adminWalletInfo.circle_wallet_id?.substring(0, 20) + '...'
          });
        }
      } catch (e) {
        console.log('   ⚠️  Could not fetch wallet info:', e.message);
      }
    }
    
    // Test 2: Login as Claimant
    console.log('\n2️⃣ Testing Claimant User...');
    const claimantRes = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        email: 'claimant@uclaim.com', 
        password: 'ClaimantDemo123!' 
      })
    });
    
    if (!claimantRes.ok) {
      const error = await claimantRes.json();
      throw new Error(`Claimant login failed: ${error.detail || claimantRes.statusText}`);
    }
    
    const claimant = await claimantRes.json();
    const claimantWallet = claimant.wallet_address;
    const claimantToken = claimant.access_token;
    
    console.log('✅ Claimant login successful');
    console.log('   Email:', claimant.email);
    console.log('   Role:', claimant.role);
    console.log('   Wallet:', claimantWallet || '❌ Missing');
    
    // Get wallet info via API
    let claimantWalletInfo = null;
    if (claimantToken) {
      try {
        const walletRes = await fetch(`${API_URL}/auth/wallet`, {
          headers: { 'Authorization': `Bearer ${claimantToken}` }
        });
        if (walletRes.ok) {
          claimantWalletInfo = await walletRes.json();
          console.log('   Wallet Info:', {
            address: claimantWalletInfo.wallet_address,
            blockchain: claimantWalletInfo.blockchain,
            circle_wallet_id: claimantWalletInfo.circle_wallet_id?.substring(0, 20) + '...'
          });
        }
      } catch (e) {
        console.log('   ⚠️  Could not fetch wallet info:', e.message);
      }
    }
    
    // Test 3: Compare Wallet Addresses
    console.log('\n3️⃣ Comparing Wallet Addresses...');
    console.log('='.repeat(50));
    
    if (!adminWallet || !claimantWallet) {
      console.log('❌ FAIL: One or both wallets are missing');
      console.log('   Admin wallet:', adminWallet || 'null');
      console.log('   Claimant wallet:', claimantWallet || 'null');
      return { success: false, reason: 'Missing wallets' };
    }
    
    if (adminWallet === claimantWallet) {
      console.log('❌ FAIL: Wallet addresses are the SAME!');
      console.log('   Both users have:', adminWallet);
      console.log('\n   This indicates a problem:');
      console.log('   - Users should have unique wallet addresses');
      console.log('   - Check if wallets are being created correctly');
      console.log('   - Verify Circle API is working properly');
      return { 
        success: false, 
        adminWallet, 
        claimantWallet,
        reason: 'Wallets are identical' 
      };
    } else {
      console.log('✅ SUCCESS: Wallet addresses are DIFFERENT!');
      console.log('   Admin wallet:   ', adminWallet);
      console.log('   Claimant wallet:', claimantWallet);
      console.log('\n   ✅ Each user has their own unique wallet address');
      console.log('   ✅ Wallet isolation is working correctly');
      
      // Additional verification
      if (adminWalletInfo && claimantWalletInfo) {
        if (adminWalletInfo.circle_wallet_id !== claimantWalletInfo.circle_wallet_id) {
          console.log('   ✅ Circle wallet IDs are also different');
        } else {
          console.log('   ⚠️  Warning: Circle wallet IDs are the same (unexpected)');
        }
      }
      
      return { 
        success: true, 
        adminWallet, 
        claimantWallet,
        adminWalletInfo,
        claimantWalletInfo
      };
    }
    
  } catch (error) {
    console.error('\n❌ ERROR:', error.message);
    console.log('\nTroubleshooting:');
    console.log('1. Make sure backend is running on http://localhost:8000');
    console.log('2. Make sure demo users exist (run backend to auto-create them)');
    console.log('3. Check browser console for CORS errors');
    return { success: false, error: error.message };
  }
})();
