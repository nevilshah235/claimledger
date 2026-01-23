'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { WalletDisplay } from './WalletDisplay';

interface WalletConnectProps {
  onConnect: (address: string, role: string) => void;
  onDisconnect: () => void;
  address?: string;
  role?: string;
}

/**
 * WalletConnect Component
 *
 * Handles authentication and wallet display. Shows the user-controlled wallet
 * (manual settlements for admin, payouts for claimant). Programmatic/auto-settle
 * wallet is shown only on the Admin Dashboard.
 *
 * No Circle SDK needed - all wallet operations handled by backend.
 */
export function WalletConnect({ onConnect, onDisconnect, address, role }: WalletConnectProps) {
  const [walletAddress, setWalletAddress] = useState<string | undefined>(address);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // If address prop is provided, use it
    if (address) {
      setWalletAddress(address);
      return;
    }

    // Otherwise, try to load wallet info
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('auth_token');
      if (token && !walletAddress) {
        loadWalletInfo();
      }
    }
  }, [address]);

  const loadWalletInfo = async () => {
    setLoading(true);
    try {
      // First try to get wallet info directly
      try {
        const walletInfo = await api.auth.getWallet();
        if (walletInfo.wallet_address) {
          setWalletAddress(walletInfo.wallet_address);
          if (role) {
            onConnect(walletInfo.wallet_address, role);
          }
          return;
        }
      } catch (walletErr) {
        // If getWallet fails, try getting user info
        console.log('getWallet failed, trying user info:', walletErr);
      }

      // Fallback to user info
      const userInfo = await api.auth.me();
      if (userInfo.wallet_address) {
        setWalletAddress(userInfo.wallet_address);
        if (userInfo.role) {
          onConnect(userInfo.wallet_address, userInfo.role);
        }
      }
    } catch (err) {
      // Not logged in or error - but don't logout, just don't show wallet
      console.warn('Failed to load wallet info:', err);
    } finally {
      setLoading(false);
    }
  };

  // Show wallet display if we have an address (from props or loaded)
  if (walletAddress) {
    return (
      <div className="flex items-center gap-2 relative z-50">
        <WalletDisplay walletAddress={walletAddress} role={role} />
      </div>
    );
  }

  // Show loading state while fetching
  if (loading) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 rounded-xl border-2 bg-blue/80 border-blue shadow-lg shadow-blue/30">
        <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
        <span className="text-xs text-white">Loading wallet...</span>
      </div>
    );
  }

  // Don't render anything if no wallet address available
  return null;
}

export default WalletConnect;
