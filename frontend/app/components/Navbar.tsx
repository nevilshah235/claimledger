'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { WalletConnect } from './WalletConnect';
import { UserMenu } from './UserMenu';
import { Button } from './ui';
import { useAuth } from '../providers/AuthProvider';

interface NavbarProps {
  walletAddress?: string;
  role?: string;
  onConnect?: (address: string, role: string) => void;
  onDisconnect?: () => void;
  onOpenLoginModal?: (role?: 'claimant' | 'insurer') => void;
}

export function Navbar({ walletAddress, role, onConnect, onDisconnect, onOpenLoginModal }: NavbarProps) {
  const { user, token, walletAddress: authWalletAddress, role: authRole, loading } = useAuth();
  const [mounted, setMounted] = useState(false);
  
  // Ensure we only render auth-dependent content after client-side hydration
  useEffect(() => {
    setMounted(true);
  }, []);
  
  // Use auth context values if available, fall back to props for backward compatibility
  // During SSR and initial render, show unauthenticated state to avoid hydration mismatch
  const isAuthenticated = mounted && !loading && !!(user || token);
  const effectiveWalletAddress = authWalletAddress ?? walletAddress;
  const effectiveRole = authRole ?? role;

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 pt-4 px-4">
      <div className="navbar-floating max-w-7xl mx-auto overflow-visible">
        <div className="px-4 sm:px-6 lg:px-8 py-3 overflow-visible">
          <div className="flex items-center h-10 overflow-visible w-full relative">
            {/* Left section: Logo */}
            <div className="flex items-center gap-6 lg:gap-8 shrink-0">
              {/* Brand (compact) */}
              <Link href="/" className="shrink-0 flex items-center">
                <Image
                  src="/uclaim-logo-transparent.png"
                  alt="UClaim"
                  width={220}
                  height={60}
                  className="h-40 sm:h-70 w-auto mt-5"
                  unoptimized
                  priority
                />
              </Link>
            </div>

            {/* Center section: Dashboard text - absolutely centered */}
            <div className="absolute left-1/2 transform -translate-x-1/2 hidden md:block">
              <div className="flex items-center gap-4 lg:gap-6 text-sm font-semibold text-text-secondary font-quando">
              {isAuthenticated && effectiveRole ? (
                <Link 
                  href={effectiveRole === 'insurer' ? '/insurer' : '/claimant'} 
                  className="hover:text-text-primary transition-colors"
                >
                  {effectiveRole === 'insurer' ? 'Admin Dashboard' : 'Claimant Dashboard'}
                </Link>
              ) : (
                <>
                  <Link href="/#steps" className="hover:text-text-primary transition-colors whitespace-nowrap">
                    How It Works
                  </Link>
                  <Link href="/#claim-flow" className="hover:text-text-primary transition-colors whitespace-nowrap">
                    Technology
                  </Link>
                  <Link href="/#trust" className="hover:text-text-primary transition-colors whitespace-nowrap">
                    Security
                  </Link>
                  <Link href="/#metrics" className="hover:text-text-primary transition-colors whitespace-nowrap">
                    Performance
                  </Link>
                </>
              )}
              </div>
            </div>

            {/* Auth/Wallet - pushed to the right */}
            <div className="flex items-center gap-3 relative z-50 shrink-0 ml-auto">
              {isAuthenticated ? (
                <>
                  <WalletConnect
                    address={effectiveWalletAddress || undefined}
                    role={effectiveRole}
                    onConnect={onConnect || (() => {})}
                    onDisconnect={onDisconnect || (() => {})}
                  />
                  <UserMenu align="right" />
                </>
              ) : (
                <>
                  <Button 
                    variant="primary" 
                    size="sm"
                    onClick={() => onOpenLoginModal?.('claimant')}
                    className="font-quando"
                  >
                    File a claim
                  </Button>
                  <Button 
                    variant="secondary" 
                    size="sm"
                    onClick={() => onOpenLoginModal?.()}
                    className="font-quando"
                  >
                    Sign in
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
