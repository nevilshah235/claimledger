'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../providers/AuthProvider';

type Role = 'claimant' | 'insurer';

export function RequireRole({
  role,
  children,
}: {
  role: Role;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (loading) return;

    if (!user) {
      // Redirect to home page instead of deprecated login page
      router.replace('/');
      return;
    }

    if (user.role !== role) {
      // Redirect to the correct home for their actual role
      router.replace(user.role === 'insurer' ? '/insurer' : '/claimant');
    }
  }, [loading, role, router, user]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="text-center">
          <svg className="w-10 h-10 text-cyan-400 animate-spin mx-auto mb-4" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <p className="text-slate-400">Loading session…</p>
        </div>
      </div>
    );
  }

  if (!user || user.role !== role) return null;

  return <>{children}</>;
}

export default RequireRole;

