'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import { Modal, Button } from './ui';
import { api } from '@/lib/api';
import { WalletInfo } from '@/lib/types';

interface WalletInfoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onWalletNotFound?: () => void; // Callback when wallet is not found
}

export function WalletInfoModal({ isOpen, onClose, onWalletNotFound }: WalletInfoModalProps) {
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

  const formatAddress = (address: string) => {
    return `${address.slice(0, 8)}...${address.slice(-8)}`;
  };


  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Circle Wallet Information" size="lg">
      <div className="space-y-6">
        {/* Header with Circle and Arc logos */}
        <div className="flex items-center justify-center gap-4 pb-4 border-b border-white/10">
          <div className="relative h-8 w-auto bg-white rounded-lg px-2 py-1 flex items-center">
            <Image
              src="/icons/circle-logo.png"
              alt="Circle"
              width={120}
              height={40}
              className="h-8 w-auto object-contain"
              unoptimized
            />
          </div>
          <span className="text-admin-text-secondary">+</span>
          <div className="relative h-8 w-auto">
            <Image
              src="/icons/arc-logo.png"
              alt="Arc"
              width={120}
              height={40}
              className="h-8 w-auto object-contain"
              unoptimized
            />
          </div>
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
            {/* Wallet Address */}
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wide admin-text-secondary">
                Wallet Address
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

            {/* Balance */}
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wide admin-text-secondary">
                Balance
              </label>
              <div className="p-4 rounded-xl bg-gradient-to-r from-blue-cobalt/20 to-blue-navy/20 border border-blue-cobalt/30">
                {walletInfo.balance && walletInfo.balance.balances && walletInfo.balance.balances.length > 0 ? (
                  <div className="space-y-3">
                    {walletInfo.balance.balances.map((tb: any, idx: number) => {
                      // Show raw token amount, not decimal-adjusted
                      const amount = parseFloat(tb.amount || '0');
                      const symbol = tb.token?.symbol || 'Unknown';
                      const name = tb.token?.name || symbol;
                      
                      // Get currency symbol based on token symbol
                      const getCurrencySymbol = (sym: string) => {
                        const upperSym = sym.toUpperCase();
                        if (upperSym.includes('EURC') || upperSym.includes('EUR')) {
                          return '€';
                        }
                        if (upperSym.includes('USDC') || upperSym.includes('USD')) {
                          return '$';
                        }
                        return '';
                      };
                      
                      const currencySymbol = getCurrencySymbol(symbol);
                      
                      return (
                        <div key={idx} className="flex items-center justify-between p-2 rounded-lg bg-white/5 border border-white/10">
                          <div className="flex-1">
                            <div className="text-sm font-semibold admin-text-primary">{name}</div>
                            <div className="text-xs admin-text-secondary">{symbol}</div>
                          </div>
                          <div className="text-right">
                            <div className="text-lg font-bold admin-text-primary">
                              {currencySymbol}{amount.toLocaleString()}
                            </div>
                            <div className="text-xs admin-text-secondary">amount</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <p className="text-sm admin-text-secondary">No tokens found</p>
                  </div>
                )}
              </div>
            </div>

            {/* Wallet Details */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase tracking-wide admin-text-secondary">
                  Circle Wallet ID
                </label>
                <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                  <code className="text-sm font-mono admin-text-primary break-all">
                    {walletInfo.circle_wallet_id || 'N/A'}
                  </code>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase tracking-wide admin-text-secondary">
                  Blockchain
                </label>
                <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                  <span className="text-sm font-medium admin-text-primary">
                    {walletInfo.blockchain || 'ARC-TESTNET'}
                  </span>
                </div>
              </div>
            </div>

            {walletInfo.wallet_set_id && (
              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase tracking-wide admin-text-secondary">
                  Wallet Set ID
                </label>
                <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                  <code className="text-sm font-mono admin-text-primary break-all">
                    {walletInfo.wallet_set_id}
                  </code>
                </div>
              </div>
            )}

            {/* Additional Info */}
            <div className="pt-4 border-t border-white/10">
              <p className="text-xs admin-text-secondary">
                This wallet is managed by Circle and connected to your account. 
                All transactions are processed on the Arc blockchain network.
              </p>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}

export default WalletInfoModal;
