'use client';

import { useState, useEffect } from 'react';
import { Button } from './ui';
import { api } from '@/lib/api';
import { WalletInfo } from '@/lib/types';

interface WalletDisplayProps {
  walletAddress?: string;
  onRefresh?: () => void;
}

/**
 * WalletDisplay Component
 * 
 * Displays wallet information from backend (Developer-Controlled wallets).
 * No Circle SDK needed - all data comes from backend API.
 */
export function WalletDisplay({ walletAddress, onRefresh }: WalletDisplayProps) {
  const [walletInfo, setWalletInfo] = useState<WalletInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (walletAddress) {
      loadWalletInfo();
    }
  }, [walletAddress]);

  const loadWalletInfo = async () => {
    setLoading(true);
    setError(null);
    try {
      const info = await api.auth.getWallet();
      setWalletInfo(info);
    } catch (err: any) {
      setError(err.message || 'Failed to load wallet info');
    } finally {
      setLoading(false);
    }
  };

  const truncateAddress = (addr: string) => {
    return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10">
        <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
        <span className="text-sm text-slate-400">Loading wallet...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-500/10 border border-red-500/30">
        <span className="text-sm text-red-400">{error}</span>
        {onRefresh && (
          <Button variant="ghost" size="sm" onClick={onRefresh}>
            Retry
          </Button>
        )}
      </div>
    );
  }

  const displayAddress = walletInfo?.wallet_address || walletAddress;

  if (!displayAddress) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10">
      <div className="w-2 h-2 rounded-full bg-emerald-400" />
      <span className="text-sm font-medium text-white font-mono">
        {truncateAddress(displayAddress)}
      </span>
      {walletInfo?.balance && (
        <span className="text-xs text-slate-400">
          (Balance: {walletInfo.balance.balances?.[0]?.amount || '0'} USDC)
        </span>
      )}
    </div>
  );
}
