'use client';

import { useEffect } from 'react';
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
 * Handles authentication and wallet display using our own auth system.
 * Wallets are automatically provisioned via Developer-Controlled Wallets (backend-only).
 * 
 * No Circle SDK needed - all wallet operations handled by backend.
 */
export function WalletConnect({ onConnect, onDisconnect, address, role }: WalletConnectProps) {
  useEffect(() => {
    // Check if user is already logged in
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('auth_token');
      if (token) {
        // Load wallet info
        loadUserInfo();
      }
    }
  }, []);

  const loadUserInfo = async () => {
    try {
      const userInfo = await api.auth.me();
      if (userInfo.wallet_address) {
        onConnect(userInfo.wallet_address, userInfo.role);
      }
    } catch (err) {
      // Not logged in or error
      api.auth.logout();
    }
  };

  if (address) {
    return (
      <div className="flex items-center gap-2">
        <WalletDisplay walletAddress={address} />
      </div>
    );
  }

  return null;
}

export default WalletConnect;
