'use client';

import Link from 'next/link';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Button } from './ui';

type Role = 'claimant' | 'insurer';
type Align = 'left' | 'right';

const ROLE_OPTIONS: Array<{ role: Role; label: string; description: string }> = [
  { role: 'claimant', label: 'Claimant', description: 'Submit and track claims' },
  { role: 'insurer', label: 'Administrator', description: 'Review and settle claims' },
];

export function LoginDropdown({
  buttonLabel = 'Log in',
  variant = 'secondary',
  size = 'sm',
  align = 'right',
  fullWidth = false,
  className = '',
}: {
  buttonLabel?: string;
  variant?: 'primary' | 'secondary' | 'success' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  align?: Align;
  fullWidth?: boolean;
  className?: string;
}) {
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

  return (
    <div ref={containerRef} className={`relative ${fullWidth ? 'w-full' : ''} ${className}`}>
      <Button
        type="button"
        variant={variant}
        size={size}
        className={fullWidth ? 'w-full justify-between' : ''}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="inline-flex items-center gap-2">
          {buttonLabel}
          <svg className="w-4 h-4 opacity-80" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path
              fillRule="evenodd"
              d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.24a.75.75 0 01-1.06 0L5.21 8.29a.75.75 0 01.02-1.08z"
              clipRule="evenodd"
            />
          </svg>
        </span>
      </Button>

      {open && (
        <div
          role="menu"
          aria-label="Login role selection"
          className={`absolute ${menuSideClass} mt-2 w-72 rounded-xl border border-border bg-surface shadow-lg backdrop-blur-0 z-50 overflow-hidden`}
        >
          <div className="p-2">
            {ROLE_OPTIONS.map((opt) => (
              <Link
                key={opt.role}
                href={`/login?role=${opt.role}`}
                role="menuitem"
                className="block rounded-lg px-3 py-2 hover:bg-surface-muted transition-colors"
                onClick={() => setOpen(false)}
              >
                <div className="text-sm font-semibold text-text-primary">{opt.label}</div>
                <div className="text-xs text-text-secondary">{opt.description}</div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default LoginDropdown;
