'use client';

import { useState, useEffect } from 'react';
import { Modal, Button } from './ui';
import { api } from '@/lib/api';
import { WalletInfo } from '@/lib/types';
import { useAuth } from '../providers/AuthProvider';

interface WalletInfoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onWalletNotFound?: () => void; // Callback when wallet is not found
}

export function WalletInfoModal({ isOpen, onClose, onWalletNotFound }: WalletInfoModalProps) {
  const { role } = useAuth();
  const [walletInfo, setWalletInfo] = useState<WalletInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadWalletInfo();
    }
  }, [isOpen]);

  const loadWalletInfo = async () => {
    setLoading(true);
    setError(null);
    try {
      const info = await api.auth.getWallet();
      setWalletInfo(info);
      setLoading(false);
    } catch (err: any) {
      const errorMessage = err.message || err.detail || 'Failed to load wallet information';
      const statusCode = err.status || err.statusCode || (err.response?.status);
      
      // Check if error indicates wallet not found (404 or specific error messages)
      const errorLower = errorMessage.toLowerCase();
      const isWalletNotFound = statusCode === 404 ||
                               errorLower.includes('wallet not found') ||
                               errorLower.includes('not found for user') ||
                               errorLower.includes('please create a wallet') ||
                               errorLower.includes('http 404') ||
                               errorLower.includes('404');
      
      setError(errorMessage);
      setLoading(false);
      
      // If wallet not found, automatically trigger enable wallet flow
      if (isWalletNotFound && onWalletNotFound) {
        // Clear settlements enabled flag since wallet is confirmed missing
        if (typeof window !== 'undefined') {
          localStorage.removeItem('uclaim_settlements_enabled');
        }
        
        // Close this modal and trigger enable wallet flow after a brief delay
        setTimeout(() => {
          onClose();
          setTimeout(() => {
            onWalletNotFound();
          }, 200);
        }, 300);
      }
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const modalTitle = role === 'insurer' ? 'Manual Wallet' : 'Your Wallet';

  const desc =
    role === 'insurer'
      ? 'You sign when you click Settle. Fund with USDC and ARC for gas.'
      : 'Your wallet for receiving claim payouts. Fund with USDC.';

  const usdcBalance = (() => {
    if (!walletInfo?.balance?.balances?.length) return null;
    const tb = walletInfo.balance.balances.find(
      (b: any) => (b.token?.symbol || '').toUpperCase().includes('USDC')
    );
    if (!tb) return null;
    const n = parseFloat(tb.amount || '0') || 0;
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
  })();

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={modalTitle} size="lg">
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 text-xs font-medium rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
            User-Controlled
          </span>
          <span className="text-xs admin-text-secondary">{desc}</span>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-8">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-4 border-blue-cobalt border-t-transparent rounded-full animate-spin" />
              <p className="text-sm admin-text-secondary">Loading wallet information...</p>
            </div>
          </div>
        )}

        {error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30">
            <p className="text-sm text-red-400">{error}</p>
            <div className="flex gap-2 mt-3">
              <Button
                variant="secondary"
                size="sm"
                onClick={loadWalletInfo}
              >
                Retry
              </Button>
              {(error.toLowerCase().includes('wallet not found') ||
                error.toLowerCase().includes('not found for user') ||
                error.toLowerCase().includes('please create a wallet')) && onWalletNotFound && (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    onClose();
                    setTimeout(() => {
                      onWalletNotFound();
                    }, 100);
                  }}
                >
                  Enable Wallet
                </Button>
              )}
            </div>
          </div>
        )}

        {walletInfo && !loading && (
          <>
            {/* Address */}
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wide admin-text-secondary">
                ADDRESS
              </label>
              <div className="flex items-center gap-2 p-3 rounded-xl bg-white/5 border border-white/10">
                <code className="flex-1 text-sm font-mono admin-text-primary break-all">
                  {walletInfo.wallet_address}
                </code>
                <button
                  onClick={() => copyToClipboard(walletInfo.wallet_address)}
                  className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 transition-colors text-xs font-medium admin-text-primary"
                >
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            </div>

            {/* USDC Balance + Blockchain */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase tracking-wide admin-text-secondary">
                  USDC BALANCE
                </label>
                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                  <span className="text-lg font-bold admin-text-primary">
                    {usdcBalance ?? '$0.00'}
                  </span>
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase tracking-wide admin-text-secondary">
                  BLOCKCHAIN
                </label>
                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                  <span className="text-lg font-bold text-cyan-400">
                    {walletInfo.blockchain || 'ARC-TESTNET'}
                  </span>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}

export default WalletInfoModal;
