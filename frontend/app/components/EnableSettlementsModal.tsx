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
    
    // Check if App ID is available
    api.auth.circleConnectInit()
      .then(init => {
        setAppIdAvailable(init.available && !!init.app_id);
      })
      .catch((err: any) => {
        if (err?.message?.includes('401') || err?.message?.includes('Unauthorized')) {
          setAppIdAvailable(false); // Hide modal if not authenticated
        } else {
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
      if (!init.available || !init.app_id || !init.user_token || !init.encryption_key || !init.challenge_id) {
        throw new Error(init.message || 'Circle connect is not available in this environment.');
      }
      
      // Validate App ID before initializing SDK
      if (!init.app_id || init.app_id.trim() === '') {
        throw new Error('Circle App ID is missing. Please configure CIRCLE_APP_ID in backend/.env');
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
            return resolve();
          });
        } catch (e) {
          console.error('Circle SDK initialization error:', e);
          reject(e);
        }
      });

      // Persist wallet mapping server-side
      await api.auth.circleConnectComplete();
      setSettlementsEnabled(true);
      await refresh();
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
      
      // Handle App ID errors specifically
      const errorMessage = e?.message || '';
      const errorCode = e?.code || '';
      const errorString = `${errorMessage} ${errorCode}`.toLowerCase();
      
      if (errorString.includes('app id') || errorString.includes('not recognized') || errorString.includes('not configured') || errorString.includes('invalid app') || errorCode === '155114') {
        setError('Circle App ID is not recognized. This usually means: (1) The App ID doesn\'t match your Circle Console, (2) Your domain (localhost) is not whitelisted in Circle Console, or (3) There\'s an environment mismatch (Testnet vs Mainnet). Check Circle Console → User Controlled Wallets → Authentication Methods → Allowed Domain and ensure localhost is whitelisted.');
      } else if (errorMessage.includes('401') || errorMessage.includes('Unauthorized')) {
        setError('Please log in to enable settlements');
      } else {
        setError(errorMessage || e?.code || "We couldn't connect right now.");
      }
      setStep('intro');
    }
  };

  // Hide modal if auth is loading, not authenticated, or App ID not available
  if (loading || !user || !token || appIdAvailable === false) {
    return null;
  }

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
            <div className="relative h-20 w-auto">
              <Image 
                src="/icons/circle-logo.png" 
                alt="Circle" 
                width={100} 
                height={100}
                className="h-20 w-auto object-contain"
                unoptimized
              />
            </div>
            <div className="text-slate-400 text-3xl font-semibold">+</div>
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
          <h2 className="text-2xl font-bold text-slate-900 mb-3">
            Enable On-Chain Payments
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed">
            You can explore claims without this. Enable now to send and receive on-chain payouts.
          </p>
        </div>

        {error && (
          <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
            {error}
          </div>
        )}

        {step === 'connecting' ? (
          <Card className="text-center py-8 bg-slate-50 border-slate-200">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-cyan-400 to-blue-500 mb-4">
              <svg className="w-8 h-8 text-white animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
            <p className="text-slate-900 text-sm font-medium">Connecting your wallet…</p>
            <p className="text-slate-600 text-xs mt-2">This will only take a moment</p>
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
        <div className="rounded-lg bg-blue-50 border border-blue-200 p-4">
          <div className="flex items-start gap-3">
            <span className="text-xl">💡</span>
            <div className="flex-1">
              <p className="text-xs text-slate-700 leading-relaxed">
                <strong className="text-slate-900 font-semibold">Good to know:</strong> Network fees are covered by the app where supported. This will only be required when you initiate on-chain actions.
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
    setEnabled(getSettlementsEnabled());
  }, []);

  return { enabled, setEnabled: (v: boolean) => { setSettlementsEnabled(v); setEnabled(v); } };
}

export default EnableSettlementsModal;
