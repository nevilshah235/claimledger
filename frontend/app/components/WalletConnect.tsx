'use client';

import { useState, useCallback } from 'react';
import { Button, Modal } from './ui';

interface WalletConnectProps {
  onConnect: (address: string) => void;
  onDisconnect: () => void;
  address?: string;
}

/**
 * WalletConnect Component
 * 
 * This is a mock implementation for the demo.
 * In production, this would integrate with Circle Wallets SDK:
 * 
 * ```typescript
 * import { W3SSdk } from '@circle-fin/w3s-pnp-web';
 * 
 * const sdk = new W3SSdk({
 *   appId: process.env.NEXT_PUBLIC_CIRCLE_APP_ID!,
 * });
 * 
 * await sdk.performLogin({
 *   deviceToken: 'your-device-token',
 * });
 * ```
 * 
 * See: https://developers.circle.com/w3s/docs/web-sdk-ui-customizations
 */
export function WalletConnect({ onConnect, onDisconnect, address }: WalletConnectProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);

  const handleConnect = useCallback(async (type: 'circle' | 'demo') => {
    setIsConnecting(true);
    
    try {
      if (type === 'circle') {
        // TODO: Implement real Circle Wallets SDK connection
        // const sdk = new W3SSdk({ appId: process.env.NEXT_PUBLIC_CIRCLE_APP_ID! });
        // const result = await sdk.performLogin({ ... });
        // onConnect(result.address);
        
        // For now, use demo address
        await new Promise(resolve => setTimeout(resolve, 1000));
        onConnect('0xCIRCLE00000000000000000000000000000000000');
      } else {
        // Demo mode - use mock address
        await new Promise(resolve => setTimeout(resolve, 500));
        onConnect('0xDEMO0000000000000000000000000000000000000');
      }
      
      setIsModalOpen(false);
    } catch (error) {
      console.error('Wallet connection failed:', error);
    } finally {
      setIsConnecting(false);
    }
  }, [onConnect]);

  const handleDisconnect = useCallback(() => {
    onDisconnect();
    setIsModalOpen(false);
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
          onClose={() => setIsModalOpen(false)}
          title="Wallet Settings"
          size="sm"
        >
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-white/5">
              <p className="text-sm text-slate-400 mb-1">Connected Address</p>
              <p className="font-mono text-white break-all">{address}</p>
            </div>
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
        onClose={() => setIsModalOpen(false)}
        title="Connect Wallet"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-400">
            Choose how you want to connect your wallet
          </p>

          {/* Circle Wallets Option */}
          <button
            onClick={() => handleConnect('circle')}
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

          {/* Demo Mode Option */}
          <button
            onClick={() => handleConnect('demo')}
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
