'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Button } from './ui';
import { useAuth } from '../providers/AuthProvider';
import { WalletInfoModal } from './WalletInfoModal';
import { AutoSettleWalletModal } from './AutoSettleWalletModal';

type Align = 'left' | 'right';

export function UserMenu({
  align = 'right',
  className = '',
}: {
  align?: Align;
  className?: string;
}) {
  const { user, logout, role } = useAuth();
  const [open, setOpen] = useState(false);
  const [showWalletModal, setShowWalletModal] = useState(false);
  const [showAutoSettleModal, setShowAutoSettleModal] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const menuSideClass = useMemo(() => (align === 'right' ? 'right-0' : 'left-0'), [align]);

  useEffect(() => {
    function onDocMouseDown(e: MouseEvent) {
      if (!containerRef.current) return;
      if (containerRef.current.contains(e.target as Node)) return;
      setOpen(false);
    }
    function onEsc(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onDocMouseDown);
    document.addEventListener('keydown', onEsc);
    return () => {
      document.removeEventListener('mousedown', onDocMouseDown);
      document.removeEventListener('keydown', onEsc);
    };
  }, []);

  // Get user initial from email or name
  const getUserInitial = () => {
    if (user?.email) {
      return user.email.charAt(0).toUpperCase();
    }
    return 'U';
  };

  const handleLogout = () => {
    setOpen(false);
    logout();
  };

  if (!user) {
    return null;
  }

  const roleLabel = role === 'insurer' ? 'Administrator' : 'Claimant';

  return (
    <div ref={containerRef} className={`relative z-50 ${className}`}>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className={`rounded-full w-10 h-10 p-0 flex items-center justify-center font-bold relative z-50 transition-all font-quando ${
          open
            ? role === 'insurer'
              ? 'border shadow-lg text-blue-200'
              : 'border shadow-lg text-primary-light'
            : role === 'insurer'
            ? 'bg-blue-cobalt/30 hover:bg-blue-cobalt/40 border border-blue-cobalt/50 shadow-lg shadow-blue-cobalt/20 text-blue-200'
            : 'bg-primary/30 hover:bg-primary/40 border border-primary/50 shadow-lg text-primary-light'
        }`}
        style={open ? {
          backgroundColor: role === 'insurer' ? 'rgba(0, 71, 171, 0.4)' : 'rgba(255, 183, 3, 0.4)',
          borderColor: role === 'insurer' ? 'rgba(0, 71, 171, 0.5)' : 'rgba(255, 183, 3, 0.5)',
          boxShadow: role === 'insurer' 
            ? '0 10px 15px -3px rgba(0, 71, 171, 0.2)' 
            : '0 10px 15px -3px rgba(255, 183, 3, 0.2)',
          color: role === 'insurer' ? 'rgb(191, 219, 254)' : 'rgb(255, 184, 77)'
        } : undefined}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {getUserInitial()}
        {/* Dropdown indicator - more visible */}
        <svg 
          className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 text-white bg-blue-cobalt rounded-full p-0.5 shadow-lg shadow-blue-cobalt/50 border border-white/20" 
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 9l-7 7-7-7" />
        </svg>
      </Button>

      {open && (
        <div
          role="menu"
          aria-label="User menu"
          className={`absolute ${menuSideClass} mt-2 w-72 rounded-xl border border-white/10 admin-card shadow-2xl backdrop-blur-16 z-[100] overflow-hidden`}
          style={{ zIndex: 9999 }}
        >
          <div className="p-4 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center admin-text-primary font-semibold border border-white/20">
                {getUserInitial()}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-semibold admin-text-primary truncate">
                  {user.email}
                </div>
                <div className="text-xs admin-text-secondary">{roleLabel}</div>
              </div>
            </div>
          </div>
          <div className="p-2 space-y-1">
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                setShowWalletModal(true);
              }}
              className="w-full text-left rounded-lg px-3 py-2 text-sm font-semibold admin-text-primary hover:bg-white/10 transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {role === 'insurer' ? 'View manual wallet' : 'View Wallet'}
            </button>
            {role === 'insurer' && (
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setOpen(false);
                  setShowAutoSettleModal(true);
                }}
                className="w-full text-left rounded-lg px-3 py-2 text-sm font-semibold admin-text-primary hover:bg-white/10 transition-colors flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                View automatic wallet
              </button>
            )}
            <button
              type="button"
              role="menuitem"
              onClick={handleLogout}
              className="w-full text-left rounded-lg px-3 py-2 text-sm font-semibold admin-text-primary hover:bg-red-500/20 transition-colors"
            >
              Log out
            </button>
          </div>
        </div>
      )}
      
      <WalletInfoModal
        isOpen={showWalletModal}
        onClose={() => setShowWalletModal(false)}
        onWalletNotFound={() => {
          // Set flag and dispatch event to trigger EnableSettlementsModal
          if (typeof window !== 'undefined') {
            try {
              // Clear settlements enabled flag since wallet is confirmed missing
              localStorage.removeItem('uclaim_settlements_enabled');
              localStorage.setItem('enable_wallet_flow', 'true');
              // Dispatch custom event that claimant page can listen to
              // Use a try-catch to handle any issues with event dispatching
              const event = new CustomEvent('enableWalletFlow', {
                bubbles: false,
                cancelable: false,
              });
              window.dispatchEvent(event);
            } catch (error) {
              // Fallback: if event dispatch fails, just set the flag
              // The claimant page will check the flag on next render
              console.warn('Failed to dispatch enableWalletFlow event:', error);
            }
          }
        }}
      />
      <AutoSettleWalletModal
        isOpen={showAutoSettleModal}
        onClose={() => setShowAutoSettleModal(false)}
      />
    </div>
  );
}

export default UserMenu;
