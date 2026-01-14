'use client';

import { useState, useEffect } from 'react';
import { Button } from './ui';
import { api } from '@/lib/api';
import { AuthModal } from './AuthModal';
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
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [userRole, setUserRole] = useState<string | null>(null);

  useEffect(() => {
    // Check if user is already logged in
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('auth_token');
      const role = localStorage.getItem('user_role');
      if (token && role) {
        setUserRole(role);
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

  const handleAuthSuccess = (walletAddress: string, userRole: string) => {
    setUserRole(userRole);
    onConnect(walletAddress, userRole);
    setIsModalOpen(false);
  };

  const handleDisconnect = () => {
    api.auth.logout();
    setUserRole(null);
    onDisconnect();
    setIsModalOpen(false);
  };

  // Determine role for auth modal (from props or current user)
  const authRole = (role || userRole || 'claimant') as 'claimant' | 'insurer';

  if (address) {
    return (
      <div className="flex items-center gap-2">
        <WalletDisplay walletAddress={address} />
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

        <AuthModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onSuccess={handleAuthSuccess}
          role={authRole}
        />
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
        {authRole === 'insurer' ? 'Login as Insurer' : 'Login as Claimant'}
      </Button>

      <AuthModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={handleAuthSuccess}
        role={authRole}
      />
    </>
  );
}

export default WalletConnect;
