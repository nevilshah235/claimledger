'use client';

import { useState, useEffect } from 'react';
import { Button } from './ui';
import { api } from '@/lib/api';
import { WalletInfo } from '@/lib/types';
import { useAuth } from '../providers/AuthProvider';

interface WalletDisplayProps {
  walletAddress?: string;
  onRefresh?: () => void;
  role?: string;
}

/**
 * WalletDisplay Component
 * 
 * Displays wallet information from backend (Developer-Controlled wallets).
 * No Circle SDK needed - all data comes from backend API.
 */
export function WalletDisplay({ walletAddress, onRefresh, role: roleProp }: WalletDisplayProps) {
  const { role: authRole } = useAuth();
  const role = roleProp || authRole;
  const isAdmin = role === 'insurer';
  
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
      <div className={`flex items-center gap-2 px-4 py-2 rounded-xl border ${
        isAdmin 
          ? 'bg-blue-cobalt/30 border-blue-cobalt/50 shadow-lg shadow-blue-cobalt/20' 
          : 'bg-blue/30 border-blue/50 shadow-lg shadow-blue/20'
      }`}>
        <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
        <span className="text-sm font-medium text-blue-200 font-quando">Loading wallet...</span>
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

  // Extract balance information
  const balances = walletInfo?.balance?.balances || [];
  const primaryBalance = balances[0];
  const tokenSymbol = primaryBalance?.token?.symbol || 'USDC';
  const rawAmount = primaryBalance?.amount || '0';

  return (
    <div className={`flex items-center gap-2 px-4 py-2 rounded-xl backdrop-blur-sm border ${
      isAdmin 
        ? 'bg-blue-cobalt/30 border-blue-cobalt/50 shadow-lg shadow-blue-cobalt/20' 
        : 'bg-blue/30 border-blue/50 shadow-lg shadow-blue/20'
    }`}>
      <div className={`w-2 h-2 rounded-full bg-emerald-400 ${
        isAdmin 
          ? 'shadow-md shadow-emerald-400/70' 
          : 'shadow-sm shadow-emerald-400/50'
      }`} />
      <span className="text-sm font-medium text-blue-200 font-quando font-semibold">
        {truncateAddress(displayAddress)}
      </span>
      {primaryBalance && (
        <span className="text-xs font-medium text-blue-300 font-quando">
          (Balance: {rawAmount} {tokenSymbol})
        </span>
      )}
    </div>
  );
}
