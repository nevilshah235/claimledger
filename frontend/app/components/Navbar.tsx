'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { WalletConnect } from './WalletConnect';
import { LoginDropdown } from './LoginDropdown';
import { UserMenu } from './UserMenu';
import { Button } from './ui';
import { useAuth } from '../providers/AuthProvider';

interface NavbarProps {
  walletAddress?: string;
  role?: string;
  onConnect?: (address: string, role: string) => void;
  onDisconnect?: () => void;
}

export function Navbar({ walletAddress, role, onConnect, onDisconnect }: NavbarProps) {
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
      <div className="navbar-floating max-w-7xl mx-auto">
        <div className="px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center justify-between h-10">
            {/* Brand (compact) */}
            <Link href="/" className="shrink-0 flex items-center">
              <Image
                src="/uclaim-logo-transparent.png"
                alt="UClaim"
                width={220}
                height={60}
                className="h-40 sm:h-70 w-auto mt-5"
                priority
              />
            </Link>

            {/* Links */}
            <div className="hidden md:flex items-center gap-6 text-sm font-semibold text-text-secondary">
              {isAuthenticated && effectiveRole ? (
                <Link 
                  href={effectiveRole === 'insurer' ? '/insurer' : '/claimant'} 
                  className="hover:text-text-primary transition-colors"
                >
                  {effectiveRole === 'insurer' ? 'Admin Dashboard' : 'Claimant Dashboard'}
                </Link>
              ) : (
                <Link href="/#claim-flow" className="hover:text-text-primary transition-colors">
                  How it works
                </Link>
              )}
            </div>

            {/* Auth/Wallet */}
            <div className="flex items-center gap-3">
              {isAuthenticated ? (
                <>
                  {effectiveWalletAddress && (
                    <WalletConnect
                      address={effectiveWalletAddress}
                      role={effectiveRole}
                      onConnect={onConnect || (() => {})}
                      onDisconnect={onDisconnect || (() => {})}
                    />
                  )}
                  <UserMenu align="right" />
                </>
              ) : (
                <>
                  <Link href="/login?role=claimant">
                    <Button variant="primary" size="sm">
                      File a claim
                    </Button>
                  </Link>
                  <LoginDropdown buttonLabel="Sign in" variant="secondary" size="sm" align="right" />
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
