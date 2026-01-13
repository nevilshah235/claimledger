'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Button } from './ui';

interface NavbarProps {
  walletAddress?: string;
  onConnectWallet?: () => void;
}

export function Navbar({ walletAddress, onConnectWallet }: NavbarProps) {
  const pathname = usePathname();

  const isActive = (path: string) => pathname === path;

  const truncateAddress = (address: string) => {
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50">
      <div className="glass-card rounded-none border-x-0 border-t-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg gradient-hero flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <span className="text-xl font-bold text-white">ClaimLedger</span>
            </Link>

            {/* Navigation Links */}
            <div className="hidden md:flex items-center gap-1">
              <Link
                href="/claimant"
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive('/claimant')
                    ? 'bg-white/10 text-white'
                    : 'text-slate-300 hover:text-white hover:bg-white/5'
                }`}
              >
                Claimant
              </Link>
              <Link
                href="/insurer"
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive('/insurer')
                    ? 'bg-white/10 text-white'
                    : 'text-slate-300 hover:text-white hover:bg-white/5'
                }`}
              >
                Insurer
              </Link>
            </div>

            {/* Wallet */}
            <div className="flex items-center gap-3">
              {walletAddress ? (
                <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10">
                  <div className="w-2 h-2 rounded-full bg-emerald-400" />
                  <span className="text-sm font-medium text-white">
                    {truncateAddress(walletAddress)}
                  </span>
                </div>
              ) : (
                <Button 
                  variant="primary" 
                  size="sm"
                  onClick={onConnectWallet}
                >
                  Connect Wallet
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
