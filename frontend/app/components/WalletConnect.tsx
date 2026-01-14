'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { Button, Modal } from './ui';
import { api } from '@/lib/api';

interface WalletConnectProps {
  onConnect: (address: string, userToken?: string) => void;
  onDisconnect: () => void;
  address?: string;
  userToken?: string;
}

/**
 * WalletConnect Component
 * 
 * Integrates with Circle Wallets SDK for user-controlled wallet authentication.
 * Falls back to demo mode if Circle SDK is not available or configured.
 * 
 * Uses Circle Wallets SDK: @circle-fin/w3s-pw-web-sdk
 * See: https://developers.circle.com/w3s/docs/web-sdk-ui-customizations
 */
export function WalletConnect({ onConnect, onDisconnect, address, userToken }: WalletConnectProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sdkRef = useRef<any>(null);

  // Initialize Circle SDK on mount (if available)
  // Note: SDK is loaded dynamically at runtime to avoid build-time bundling issues
  useEffect(() => {
    const initSDK = async () => {
      const appId = process.env.NEXT_PUBLIC_CIRCLE_APP_ID;
      if (!appId) {
        console.warn('NEXT_PUBLIC_CIRCLE_APP_ID not configured, Circle SDK disabled');
        return;
      }

      // Only run on client side
      if (typeof window === 'undefined') {
        return;
      }

      // SDK will be loaded dynamically when needed, not at component mount
      // This avoids build-time bundling issues
      sdkRef.current = { appId, initialized: false };
    };

    initSDK();
  }, [userToken]);

  const handleCircleConnect = useCallback(async () => {
    setIsConnecting(true);
    setError(null);
    
    try {
      const appId = process.env.NEXT_PUBLIC_CIRCLE_APP_ID;
      if (!appId) {
        throw new Error('NEXT_PUBLIC_CIRCLE_APP_ID not configured');
      }

      // Only run on client side
      if (typeof window === 'undefined') {
        throw new Error('Circle authentication must run in browser');
      }

      // Step 1: Initialize authentication with backend
      const initResponse = await api.auth.initCircle();
      const { user_id, user_token, challenge_id, app_id: backendAppId } = initResponse;

      // Step 2: Dynamically load Circle SDK at runtime using Function constructor
      // This prevents Next.js from analyzing the import at build time
      let W3SSdk: any;
      try {
        // Use Function constructor to create a dynamic import that Next.js can't analyze
        const importSDK = new Function('return import("@circle-fin/w3s-pw-web-sdk")');
        const sdkModule = await importSDK();
        W3SSdk = sdkModule.W3SSdk || sdkModule.default?.W3SSdk;
        
        if (!W3SSdk) {
          throw new Error('W3SSdk not found in Circle SDK module');
        }
      } catch (importErr: any) {
        console.error('Failed to load Circle SDK:', importErr);
        throw new Error(`Circle SDK failed to load: ${importErr.message || 'Unknown error'}. Please check your environment configuration.`);
      }

      // Initialize SDK instance
      const sdk = new W3SSdk({
        configs: {
          appSettings: { appId: backendAppId || appId },
          authentication: {
            userToken: user_token,
            encryptionKey: undefined,
          },
          socialLoginConfig: {},
        },
        socialLoginCompleteCallback: (error: any, result: any) => {
          if (error) {
            console.error('Circle social login error:', error);
          }
        },
      });

      // Step 3: Execute challenge with Circle SDK
      // This shows Circle's authentication UI
      await new Promise<void>((resolve, reject) => {
        try {
          sdk.execute(
            challenge_id,
            (error: any, result: any) => {
              if (error) {
                reject(new Error(error.message || 'Circle authentication failed'));
                return;
              }

              if (result && result.data && result.data.wallets && result.data.wallets.length > 0) {
                // Step 4: Get wallet address from result
                const walletAddress = result.data.wallets[0].address;
                const circleWalletId = result.data.wallets[0].id;

                // Step 5: Complete authentication with backend
                api.auth.completeCircle({
                  user_token: user_token,
                  wallet_address: walletAddress,
                  circle_wallet_id: circleWalletId,
                }).then(() => {
                  onConnect(walletAddress, user_token);
                  setIsModalOpen(false);
                  resolve();
                }).catch((err) => {
                  reject(err);
                });
              } else {
                reject(new Error('No wallet found in authentication result'));
              }
            }
          );
        } catch (err: any) {
          reject(new Error(err.message || 'Failed to execute Circle SDK'));
        }
      });
    } catch (err: any) {
      console.error('Circle wallet connection failed:', err);
      setError(err.message || 'Failed to connect Circle wallet');
    } finally {
      setIsConnecting(false);
    }
  }, [onConnect]);

  const handleDemoConnect = useCallback(async () => {
    setIsConnecting(true);
    setError(null);
    
    try {
      // Demo mode - use mock address
      await new Promise(resolve => setTimeout(resolve, 500));
      onConnect('0xDEMO0000000000000000000000000000000000000');
      setIsModalOpen(false);
    } catch (err: any) {
      console.error('Demo wallet connection failed:', err);
      setError(err.message || 'Failed to connect demo wallet');
    } finally {
      setIsConnecting(false);
    }
  }, [onConnect]);

  const handleDisconnect = useCallback(() => {
    onDisconnect();
    setIsModalOpen(false);
    setError(null);
  }, [onDisconnect]);

  const truncateAddress = (addr: string) => {
    return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
  };

  if (address) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10">
          <div className="w-2 h-2 rounded-full bg-emerald-400" />
          <span className="text-sm font-medium text-white">
            {truncateAddress(address)}
          </span>
        </div>
        <Button 
          variant="ghost" 
          size="sm"
          onClick={() => setIsModalOpen(true)}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </Button>

        {/* Settings Modal */}
        <Modal
          isOpen={isModalOpen}
          onClose={() => {
            setIsModalOpen(false);
            setError(null);
          }}
          title="Wallet Settings"
          size="sm"
        >
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-white/5">
              <p className="text-sm text-slate-400 mb-1">Connected Address</p>
              <p className="font-mono text-white break-all">{address}</p>
            </div>
            {error && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30">
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}
            <Button
              variant="secondary"
              className="w-full"
              onClick={handleDisconnect}
            >
              Disconnect Wallet
            </Button>
          </div>
        </Modal>
      </div>
    );
  }

  const isCircleAvailable = process.env.NEXT_PUBLIC_CIRCLE_APP_ID !== undefined;

  return (
    <>
      <Button 
        variant="primary" 
        size="sm"
        onClick={() => setIsModalOpen(true)}
      >
        Connect Wallet
      </Button>

      {/* Connect Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setError(null);
        }}
        title="Connect Wallet"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-400">
            Choose how you want to connect your wallet
          </p>

          {/* Circle Wallets Option */}
          {isCircleAvailable ? (
            <button
              onClick={handleCircleConnect}
              disabled={isConnecting}
              className="w-full p-4 rounded-xl border border-white/10 hover:border-cyan-500/50 hover:bg-white/5 transition-all text-left disabled:opacity-50"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                  <svg className="w-5 h-5 text-blue-400" viewBox="0 0 24 24" fill="currentColor">
                    <circle cx="12" cy="12" r="10" />
                  </svg>
                </div>
                <div>
                  <p className="font-medium text-white">Circle Wallets</p>
                  <p className="text-xs text-slate-400">MPC-powered, user-controlled wallet</p>
                </div>
              </div>
            </button>
          ) : (
            <div className="w-full p-4 rounded-xl border border-slate-600/50 bg-slate-800/30 opacity-50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-slate-600/20 flex items-center justify-center">
                  <svg className="w-5 h-5 text-slate-500" viewBox="0 0 24 24" fill="currentColor">
                    <circle cx="12" cy="12" r="10" />
                  </svg>
                </div>
                <div>
                  <p className="font-medium text-slate-400">Circle Wallets</p>
                  <p className="text-xs text-slate-500">Not configured (NEXT_PUBLIC_CIRCLE_APP_ID missing)</p>
                </div>
              </div>
            </div>
          )}

          {/* Demo Mode Option */}
          <button
            onClick={handleDemoConnect}
            disabled={isConnecting}
            className="w-full p-4 rounded-xl border border-white/10 hover:border-emerald-500/50 hover:bg-white/5 transition-all text-left disabled:opacity-50"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
                <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <p className="font-medium text-white">Demo Mode</p>
                <p className="text-xs text-slate-400">Use a mock wallet for testing</p>
              </div>
            </div>
          </button>

          {/* Error Display */}
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {/* Loading State */}
          {isConnecting && (
            <div className="flex items-center justify-center gap-2 py-2">
              <svg className="w-5 h-5 text-cyan-400 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span className="text-sm text-slate-400">Connecting...</span>
            </div>
          )}
        </div>
      </Modal>
    </>
  );
}

export default WalletConnect;
