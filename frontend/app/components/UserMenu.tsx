'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Button } from './ui';
import { useAuth } from '../providers/AuthProvider';

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
    <div ref={containerRef} className={`relative ${className}`}>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="rounded-full w-10 h-10 p-0 flex items-center justify-center bg-primary/20 hover:bg-primary/30 text-white font-semibold"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {getUserInitial()}
      </Button>

      {open && (
        <div
          role="menu"
          aria-label="User menu"
          className={`absolute ${menuSideClass} mt-2 w-72 rounded-xl border border-border bg-surface shadow-lg backdrop-blur-0 z-50 overflow-hidden`}
        >
          <div className="p-4 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-white font-semibold">
                {getUserInitial()}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-semibold text-text-primary truncate">
                  {user.email}
                </div>
                <div className="text-xs text-text-secondary">{roleLabel}</div>
              </div>
            </div>
          </div>
          <div className="p-2">
            <button
              type="button"
              role="menuitem"
              onClick={handleLogout}
              className="w-full text-left rounded-lg px-3 py-2 text-sm font-semibold text-red-400 hover:bg-red-500/10 transition-colors"
            >
              Log out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default UserMenu;
