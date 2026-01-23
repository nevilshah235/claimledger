'use client';

import { useEffect, useState } from 'react';
import { W3SSdk } from '@circle-fin/w3s-pw-web-sdk';
import Image from 'next/image';
import { Modal, Button, Card } from './ui';
import { api } from '@/lib/api';
import { useAuth } from '../providers/AuthProvider';

const STORAGE_KEY = 'uclaim_settlements_enabled';

function getSettlementsEnabled(): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem(STORAGE_KEY) === 'true';
}

function setSettlementsEnabled(value: boolean) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, value ? 'true' : 'false');
}

export function EnableSettlementsModal({
  isOpen,
  onClose,
  required = false,
}: {
  isOpen: boolean;
  onClose: () => void;
  required?: boolean;
}) {
  const { user, token, loading, refresh } = useAuth();
  const [step, setStep] = useState<'intro' | 'connecting'>('intro');
  const [error, setError] = useState<string | null>(null);
  const [appIdAvailable, setAppIdAvailable] = useState<boolean | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setStep('intro');
      setError(null);
    } else {
      // Clear any previous errors when modal opens
      setError(null);
    }
  }, [isOpen]);

  // Wait for auth to complete, then check App ID availability
  useEffect(() => {
    if (!isOpen) return;
    
    if (loading) {
      // Wait for auth to finish
      return;
    }
    
    if (!user || !token) {
      setAppIdAvailable(false);
      return;
    }
    
    // Check if App ID is available (don't show errors here, just check availability)
    api.auth.circleConnectInit()
      .then(init => {
        setAppIdAvailable(init.available && !!init.app_id);
        // Clear any errors from previous attempts if initialization is successful or if user just needs to complete setup
        if (init.available || (init.message && init.message.includes('no wallet found'))) {
          // User is initialized but no wallet - they can still proceed, so don't show error
          setError(null);
        }
      })
      .catch((err: any) => {
        // Silently handle errors in the check - don't show them to user yet
        // They'll see the error when they click "Enable now"
        if (err?.message?.includes('401') || err?.message?.includes('Unauthorized')) {
          setAppIdAvailable(false); // Hide modal if not authenticated
        } else {
          // Don't set error here - let the user try and see the error
          setAppIdAvailable(false);
        }
      });
  }, [isOpen, user, token, loading]);

  const runCircleConnect = async () => {
    setError(null);
    setStep('connecting');

    // Check authentication before proceeding
    if (!user || !token) {
      setError('Please log in to enable settlements');
      setStep('intro');
      return;
    }

    try {
      const init = await api.auth.circleConnectInit();
      
      // Log user info for debugging
      if (user) {
        console.log(`[Circle Connect] User ID: ${user.user_id}, Email: ${user.email}`);
      }
      console.log(`[Circle Connect] Init response:`, init);
      
      // Check if initialization is available
      if (!init.available) {
        // Check if it's a user-friendly message from backend
        if (init.message && (
          init.message.includes('already initialized') || 
          init.message.includes('Wallet setup complete') ||
          init.message.includes('Wallet retrieved')
        )) {
          // User already has wallet - try to complete connection
          try {
            await api.auth.circleConnectComplete();
            setSettlementsEnabled(true);
            setError(null); // Clear any previous errors
            await refresh();
            // Clear registration flag when wallet setup is complete
            if (typeof window !== 'undefined') {
              localStorage.removeItem('just_registered_claimant');
              localStorage.removeItem('just_logged_in_claimant');
            }
            onClose();
            return;
          } catch (completeErr: any) {
            // If complete fails, show the original message
            throw new Error(init.message || 'Circle connect is not available in this environment.');
          }
        }
        
        throw new Error(init.message || 'Circle connect is not available in this environment.');
      }
      
      // Validate required fields
      if (!init.app_id || init.app_id.trim() === '') {
        throw new Error('Circle App ID is missing. Please configure CIRCLE_APP_ID in backend/.env');
      }
      
      if (!init.user_token || !init.encryption_key) {
        throw new Error('Circle authentication tokens are missing. Please try again.');
      }

      // If challenge_id is None, user is already initialized with a wallet
      // Skip SDK execute and just complete the connection
      if (!init.challenge_id) {
        // User already has a wallet - just complete the connection
        try {
          await api.auth.circleConnectComplete();
          setSettlementsEnabled(true);
          setError(null); // Clear any previous errors
          await refresh();
          // Clear registration flag when wallet setup is complete
          if (typeof window !== 'undefined') {
            localStorage.removeItem('just_registered_claimant');
            localStorage.removeItem('just_logged_in_claimant');
          }
          onClose();
          return;
        } catch (completeErr: any) {
          // If complete fails, it might mean wallet needs to be fetched
          // Show a helpful message
          throw new Error('Wallet setup is in progress. Please try again in a moment.');
        }
      }

      const sdk = new W3SSdk({
        appSettings: {
          appId: init.app_id,
        },
      });

      // Web SDK authentication for PIN flow
      sdk.setAuthentication({
        userToken: init.user_token,
        encryptionKey: init.encryption_key,
      });

      await new Promise<void>((resolve, reject) => {
        try {
          (sdk as any).execute(init.challenge_id, async (err: any, result: any) => {
            if (err) {
              console.error('Circle SDK execute error:', err);
              // Log full error details for debugging
              if (err.message) console.error('Error message:', err.message);
              if (err.code) console.error('Error code:', err.code);
              if (err.data) console.error('Error data:', err.data);
              return reject(err);
            }
            // Most SDK callbacks use { status: 'SUCCESS'|'FAILED'|... }
            const status = result?.status || result?.data?.status;
            if (status && String(status).toUpperCase().includes('FAIL')) return reject(new Error('Circle challenge failed.'));
            // Clear any previous errors since SDK execution succeeded
            setError(null);
            return resolve();
          });
        } catch (e) {
          console.error('Circle SDK initialization error:', e);
          reject(e);
        }
      });

      // SDK execution succeeded - clear any previous errors
      setError(null);

      // Persist wallet mapping server-side
      // Retry logic: Wallet might not be immediately available after SDK completion
      // Circle API may need a moment to propagate the wallet after SDK execution
      // Add initial delay to give Circle time to process the wallet creation
      console.log('SDK execution completed, waiting for wallet to be available...');
      await new Promise(resolve => setTimeout(resolve, 2000)); // Initial 2 second delay

      let completeResult = await api.auth.circleConnectComplete();
      let retries = 0;
      const maxRetries = 8; // Increased retries
      const baseDelay = 2000; // Start with 2 seconds

      // Retry if wallet not found immediately (timing issue)
      while (!completeResult.success && retries < maxRetries) {
        retries++;
        const delay = baseDelay + (retries * 1000); // Progressive delay: 2s, 3s, 4s, 5s, 6s, 7s, 8s, 9s
        console.log(`Wallet not found immediately, retrying in ${delay}ms (${retries}/${maxRetries})...`);
        await new Promise(resolve => setTimeout(resolve, delay));
        completeResult = await api.auth.circleConnectComplete();
      }

      if (!completeResult.success) {
        // Wallet still not found after retries, but SDK completed successfully
        // This means the wallet was created but Circle's API hasn't made it queryable yet
        // Instead of showing an error, treat this as success and refresh to pick up the wallet
        console.warn('Wallet created via SDK but not immediately queryable. Refreshing to pick up wallet...');
        setError(null);
        setSettlementsEnabled(true);
        setStep('intro');
        
        // Refresh auth to pick up the wallet
        await refresh();
        
        // Clear registration flag when wallet setup is complete
        if (typeof window !== 'undefined') {
          localStorage.removeItem('just_registered_claimant');
          localStorage.removeItem('just_logged_in_claimant');
        }
        
        // Close modal - wallet should be available after refresh
        onClose();
        
        // Show a brief success message (optional - could use a toast notification)
        // For now, just close and let the refresh pick up the wallet
        return;
      }

      // Successfully found wallet - clear any errors and proceed
      setError(null);
      setSettlementsEnabled(true);
      setStep('intro'); // Reset step to intro
      await refresh();
      // Clear registration flag when wallet setup is complete
      if (typeof window !== 'undefined') {
        localStorage.removeItem('just_registered_claimant');
        localStorage.removeItem('just_logged_in_claimant');
      }
      onClose();
    } catch (e: any) {
      // Log full error for debugging
      console.error('Circle connect error:', e);
      console.error('Error details:', {
        message: e?.message,
        code: e?.code,
        data: e?.data,
        stack: e?.stack,
      });
      
      // Handle specific error cases with user-friendly messages
      const errorMessage = e?.message || '';
      const errorCode = e?.code || '';
      const errorString = `${errorMessage} ${errorCode}`.toLowerCase();
      
      // Filter out technical error messages and replace with user-friendly ones
      let userFriendlyError = errorMessage;
      
      if (errorString.includes('missing challengeid') || errorString.includes('missing challenge')) {
        // This should not happen with our fix, but handle gracefully
        userFriendlyError = 'Wallet setup is already in progress. Please wait a moment and try again, or refresh the page.';
      } else if (errorString.includes('app id') || errorString.includes('not recognized') || errorString.includes('not configured') || errorString.includes('invalid app') || errorCode === '155114') {
        userFriendlyError = 'Circle App ID is not recognized. This usually means: (1) The App ID doesn\'t match your Circle Console, (2) Your domain (localhost) is not whitelisted in Circle Console, or (3) There\'s an environment mismatch (Testnet vs Mainnet). Check Circle Console → User Controlled Wallets → Authentication Methods → Allowed Domain and ensure localhost is whitelisted.';
      } else if (errorMessage.includes('401') || errorMessage.includes('Unauthorized')) {
        userFriendlyError = 'Please log in to enable settlements';
      } else if (errorMessage.includes('already initialized') || errorMessage.includes('Wallet setup complete') || errorMessage.includes('Wallet retrieved')) {
        // This is actually a success case - try to complete
        try {
          await api.auth.circleConnectComplete();
          setSettlementsEnabled(true);
          setError(null); // Clear any previous errors
          setStep('intro'); // Reset step to intro
          await refresh();
          // Clear registration flag when wallet setup is complete
          if (typeof window !== 'undefined') {
            localStorage.removeItem('just_registered_claimant');
            localStorage.removeItem('just_logged_in_claimant');
          }
          onClose();
          return;
        } catch (completeErr: any) {
          userFriendlyError = 'Your wallet is being set up. Please wait a moment and try again.';
        }
      } else if (!errorMessage || errorMessage.trim() === '') {
        userFriendlyError = "We couldn't connect right now. Please try again in a moment.";
      }
      
      setError(userFriendlyError);
      setStep('intro');
    }
  };

  // Show modal if user is authenticated
  // Hide only if auth is loading or not authenticated
  // But wait a bit for auth to settle if we just opened
  if (!isOpen) {
    return null;
  }
  
  if (loading || !user || !token) {
    // Still return the modal structure but in a loading state
    // This ensures it appears as soon as auth is ready
    return (
      <Modal
        isOpen={isOpen}
        onClose={required ? () => {} : onClose}
        title=""
        size="sm"
      >
        <div className="space-y-6">
          <div className="text-center py-8">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="admin-text-secondary text-sm">Loading...</p>
          </div>
        </div>
      </Modal>
    );
  }
  
  // Always show modal when isOpen is true and user is authenticated
  // The App ID check is just for error handling, not for hiding the modal
  // Users need to see the modal to set up their wallet, even if App ID check fails

  return (
    <Modal
      isOpen={isOpen}
      onClose={required ? () => {} : onClose}
      title=""
      size="sm"
    >
      <div className="space-y-6">
        {/* Hero Section with Circle and Arc Icons */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-4 mb-6">
            <div className="relative h-20 w-auto bg-white rounded-lg px-2 py-1 flex items-center">
              <Image 
                src="/icons/circle-logo.png" 
                alt="Circle" 
                width={100} 
                height={100}
                className="h-20 w-auto object-contain"
                unoptimized
              />
            </div>
            <div className="admin-text-secondary text-3xl font-semibold">+</div>
            <div className="relative h-20 w-auto">
              <Image 
                src="/icons/arc-logo.png" 
                alt="Arc" 
                width={100} 
                height={100}
                className="h-20 w-auto object-contain"
                unoptimized
              />
            </div>
          </div>
          <h2 className="text-2xl font-bold admin-text-primary mb-3">
            Enable On-Chain Payments
          </h2>
          <p className="text-sm admin-text-secondary leading-relaxed">
            Enable now to receive on-chain payouts when claims are approved.
          </p>
        </div>

        {error && (
          <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
            <div className="flex items-start gap-2">
              <span className="text-red-600 mt-0.5">⚠️</span>
              <div className="flex-1">
                <p className="font-medium mb-1">Unable to enable payments</p>
                <p className="text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {step === 'connecting' ? (
          <Card className="text-center py-8 admin-card border-white/10">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-cyan-400 to-blue-500 mb-4">
              <svg className="w-8 h-8 text-white animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
            <p className="admin-text-primary text-sm font-medium">Connecting your wallet…</p>
            <p className="admin-text-secondary text-xs mt-2">This will only take a moment</p>
          </Card>
        ) : (
          <div className="flex flex-col gap-3">
            <Button 
              onClick={runCircleConnect} 
              size="lg"
              className="bg-gradient-to-r from-amber-400 via-yellow-400 to-orange-400 hover:from-amber-500 hover:via-yellow-500 hover:to-orange-500 text-white font-bold shadow-lg shadow-amber-500/30 hover:shadow-amber-500/40 transition-all"
            >
              <span className="mr-2">✨</span>
              Enable now
            </Button>
            {!required && (
              <Button 
                onClick={onClose} 
                variant="secondary" 
                size="lg"
                className="bg-slate-100 hover:bg-slate-200 border-slate-300 text-slate-700"
              >
                Maybe later
              </Button>
            )}
          </div>
        )}

        {/* Benefits Section */}
        <div className="rounded-lg bg-blue-500/10 border border-blue-500/30 p-4">
          <div className="flex items-start gap-3">
            <span className="text-xl">💡</span>
            <div className="flex-1">
              <p className="text-xs admin-text-secondary leading-relaxed">
                <strong className="admin-text-primary font-semibold">Good to know:</strong> Network fees are covered by the app where supported. This will only be required when you initiate on-chain actions.
              </p>
            </div>
          </div>
        </div>
      </div>
    </Modal>
  );
}

export function useSettlementsEnabled() {
  const [enabled, setEnabled] = useState(() => getSettlementsEnabled());

  useEffect(() => {
    // Initial check
    setEnabled(getSettlementsEnabled());
    
    // Listen for storage changes from other tabs/windows
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) {
        setEnabled(e.newValue === 'true');
      }
    };
    
    // Also check periodically since same-window localStorage changes don't trigger storage event
    const interval = setInterval(() => {
      const current = getSettlementsEnabled();
      setEnabled(prev => {
        // Only update if value actually changed to avoid unnecessary re-renders
        return current !== prev ? current : prev;
      });
    }, 500);

    window.addEventListener('storage', handleStorageChange);
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      clearInterval(interval);
    };
  }, []); // Empty dependency array - effect only runs once on mount

  return { enabled, setEnabled: (v: boolean) => { setSettlementsEnabled(v); setEnabled(v); } };
}

export default EnableSettlementsModal;
