'use client';

import { Suspense, useEffect, useMemo, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { Button, Card, Input } from './ui';
import { useAuth } from '../providers/AuthProvider';
import { api } from '@/lib/api';

type Role = 'claimant' | 'insurer';

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
  preselectedRole?: Role;
  lockRole?: boolean; // If true, hide role toggle and lock to preselectedRole
  onSuccess?: (address: string, role: string) => void;
}

function LoginFormContent({ preselectedRole = 'claimant', lockRole = false, onSuccess, onClose }: { preselectedRole?: Role; lockRole?: boolean; onSuccess?: (address: string, role: string) => void; onClose: () => void }) {
  const router = useRouter();
  const { user, loading, login, register, redirectToHome, refresh } = useAuth();

  const [role, setRole] = useState<Role>(preselectedRole);
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [adminLoginLoading, setAdminLoginLoading] = useState(false);
  const demoModeEnabled = useMemo(() => process.env.NEXT_PUBLIC_MOCK_WALLET === 'true', []);

  useEffect(() => {
    setRole(preselectedRole);
  }, [preselectedRole]);

  // Auto-login when Administrator tab is selected (only once)
  const adminLoginAttemptedRef = useRef(false);
  
  const handleAdminAutoLogin = async () => {
    if (adminLoginLoading || adminLoginAttemptedRef.current) return;
    adminLoginAttemptedRef.current = true;
    setAdminLoginLoading(true);
    setError(null);
    try {
      const response = await api.auth.adminLogin();
      await new Promise(resolve => setTimeout(resolve, 50));
      try {
        const userInfo = await refresh();
        if (userInfo) {
          // Always redirect to admin dashboard after successful auto-login
          onClose();
          router.push('/insurer');
        }
      } catch (refreshError: any) {
        if (refreshError?.message?.includes('401') || refreshError?.message?.includes('Unauthorized')) {
          if (typeof window !== 'undefined') {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user_id');
            localStorage.removeItem('user_role');
            localStorage.removeItem('just_logged_in_claimant');
          }
          setError('Admin login succeeded but authentication failed. Please try again.');
          adminLoginAttemptedRef.current = false;
        } else {
          console.warn('Refresh failed after admin login:', refreshError);
          // Still redirect to admin dashboard even if refresh fails
          onClose();
          router.push('/insurer');
        }
      }
    } catch (e: any) {
      const errorMsg = e?.message || 'Admin auto-login is not available.';
      if (errorMsg.includes('404') || errorMsg.includes('not configured') || errorMsg.includes('not found')) {
        setError('Admin auto-login is not available. Please configure ADMIN_WALLET_ADDRESS in backend environment variables.');
      } else {
        setError(`Admin login failed: ${errorMsg}`);
      }
      setAdminLoginLoading(false);
      adminLoginAttemptedRef.current = false;
    }
  };
  
  const adminLoginKeyRef = useRef<string>('');
  
  useEffect(() => {
    const currentKey = `${role}-${mode}`;
    const shouldAttempt = role === 'insurer' && 
                         mode === 'login' && 
                         !user && 
                         !adminLoginLoading && 
                         !submitting && 
                         !loading && 
                         adminLoginKeyRef.current !== currentKey;
    
    if (shouldAttempt) {
      adminLoginKeyRef.current = currentKey;
      // Slow down auto-login to 2.5 seconds so users can see what's happening
      const timeoutId = setTimeout(() => {
        handleAdminAutoLogin();
      }, 2500);
      return () => clearTimeout(timeoutId);
    }
    
    if (role !== 'insurer' && adminLoginKeyRef.current.startsWith('insurer-')) {
      adminLoginAttemptedRef.current = false;
      adminLoginKeyRef.current = '';
      setError(null);
    }
  }, [role, mode, user, adminLoginLoading, submitting, loading]);

  const redirectedRef = useRef(false);
  
  useEffect(() => {
    if (!loading && user && !adminLoginLoading && !redirectedRef.current) {
      redirectedRef.current = true;
      // Mark that user just logged in for wallet modal trigger
      if (typeof window !== 'undefined' && (user.role === 'claimant' || role === 'claimant')) {
        localStorage.setItem('just_logged_in_claimant', 'true');
      }
      if (onSuccess) {
        onSuccess(user.wallet_address || '', user.role || role);
      }
      // All claimant login flows should lead to claimant dashboard
      if (user.role === 'claimant' || role === 'claimant') {
        router.push('/claimant');
      } else if (!onSuccess) {
        // Only use redirectToHome for non-claimants when onSuccess is not provided
        redirectToHome(user.role as Role);
      }
      onClose();
    }
    if (!user && redirectedRef.current) {
      redirectedRef.current = false;
    }
  }, [loading, user, redirectToHome, adminLoginLoading, onSuccess, onClose, role, router]);

  const subtitle = mode === 'login' ? 'Sign in to continue.' : 'Create an account to submit or review claims.';

  const roleDescription = useMemo(() => {
    if (role === 'claimant') {
      return 'Log in to upload your claim details and let our AI evaluator assess them automatically.';
    }
    return 'Log in to access comprehensive data and analytics on all insurance claims.';
  }, [role]);

  async function onSubmit() {
    setError(null);
    setSubmitting(true);
    try {
      if (mode === 'login') {
        const res = await login({ email, password });
        // Mark that user just logged in for wallet modal trigger
        if (typeof window !== 'undefined' && (res.role === 'claimant' || role === 'claimant')) {
          localStorage.setItem('just_logged_in_claimant', 'true');
        }
        
        // Refresh auth state to ensure it's up to date
        await refresh();
        
        if (onSuccess) {
          onSuccess(res.wallet_address || '', res.role || role);
        }
        // All claimant login flows should lead to claimant dashboard
        if (res.role === 'claimant' || role === 'claimant') {
          router.push('/claimant');
        } else if (!onSuccess) {
          // Only use redirectToHome for non-claimants when onSuccess is not provided
          redirectToHome((res.role as Role) || role);
        }
        onClose();
        return;
      }

      const res = await register({ email, password, role });
      // Mark that user just registered (new user) for wallet modal trigger
      if (typeof window !== 'undefined' && (res.role === 'claimant' || role === 'claimant')) {
        localStorage.setItem('just_registered_claimant', 'true');
        localStorage.setItem('just_logged_in_claimant', 'true');
      }
      
      // Refresh auth state to ensure it's up to date
      await refresh();
      
      if (onSuccess) {
        onSuccess(res.wallet_address, res.role);
      }
      // All claimant login flows should lead to claimant dashboard
      if (res.role === 'claimant' || role === 'claimant') {
        router.push('/claimant');
      } else if (!onSuccess) {
        // Only use redirectToHome for non-claimants when onSuccess is not provided
        redirectToHome((res.role as Role) || role);
      }
      onClose();
    } catch (e: any) {
      setError(e?.message || 'Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  async function onDemo() {
    setError(null);
    setSubmitting(true);
    try {
      const ts = Date.now();
      const demoEmail = `demo+${role}+${ts}@example.com`;
      const demoPassword = `demo-${ts}`;
      const res = await register({ email: demoEmail, password: demoPassword, role });
      // Mark that user just registered (new user) for wallet modal trigger
      if (typeof window !== 'undefined' && (res.role === 'claimant' || role === 'claimant')) {
        localStorage.setItem('just_registered_claimant', 'true');
        localStorage.setItem('just_logged_in_claimant', 'true');
      }
      
      // Refresh auth state to ensure it's up to date
      await refresh();
      
      if (onSuccess) {
        onSuccess(res.wallet_address, res.role);
      }
      // All claimant login flows should lead to claimant dashboard
      if (res.role === 'claimant' || role === 'claimant') {
        router.push('/claimant');
      } else if (!onSuccess) {
        // Only use redirectToHome for non-claimants when onSuccess is not provided
        redirectToHome((res.role as Role) || role);
      }
      onClose();
    } catch (e: any) {
      setError(e?.message || 'Failed to start demo mode.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Card padding="lg">
        {/* Logo and subtitle */}
        <div className="mb-6 text-center">
          <div className="inline-flex flex-col items-center gap-0">
            <Image 
              src="/uclaim-logo-transparent.png" 
              alt="UClaim" 
              width={1400} 
              height={360} 
              className="h-24 w-auto"
              unoptimized
            />
            <span className="sr-only">UClaim</span>
            <p className="text-blue-metallic -mt-2 italic">{subtitle}</p>
          </div>
        </div>

        {/* Role toggle - only show if role is not locked */}
        {!lockRole && (
          <div className="mb-6">
            <div className="grid grid-cols-2 gap-2 p-1 rounded-xl bg-white/5 border border-white/10">
              <button
                type="button"
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                  role === 'claimant' ? 'bg-blue/20 text-blue border border-blue/30' : 'text-blue/70 hover:text-blue'
                }`}
                onClick={() => setRole('claimant')}
              >
                Claimant
              </button>
              <button
                type="button"
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                  role === 'insurer' ? 'bg-blue/20 text-blue border border-blue/30' : 'text-blue/70 hover:text-blue'
                }`}
                onClick={() => setRole('insurer')}
              >
                Administrator
              </button>
            </div>
            <p className="text-xs text-blue-metallic/80 mt-2 italic">
              {roleDescription}
            </p>
          </div>
        )}
        {/* Show role description even when locked */}
        {lockRole && (
          <div className="mb-6">
            <p className="text-xs text-blue-metallic/80 italic">
              {roleDescription}
            </p>
          </div>
        )}

        {/* Form */}
        <div className="space-y-4">
          {role === 'insurer' && mode === 'login' ? (
            <>
              <div className="rounded-lg border border-blue/30 bg-blue/10 px-4 py-6 text-sm text-blue-200">
                <div className="flex flex-col items-center justify-center">
                  {/* Circular animated spinner */}
                  {(adminLoginLoading || (!adminLoginAttemptedRef.current && !error)) && (
                    <div className="mb-4">
                      <div className="relative w-16 h-16">
                        {/* Outer ring */}
                        <div className="absolute inset-0 border-4 border-blue/20 rounded-full"></div>
                        {/* Animated spinner */}
                        <div className="absolute inset-0 border-4 border-blue border-t-transparent rounded-full animate-spin"></div>
                        {/* Inner pulsing circle */}
                        <div className="absolute inset-2 border-2 border-blue/40 rounded-full animate-pulse"></div>
                      </div>
                    </div>
                  )}
                  
                  <p className="font-semibold mb-2 text-center">Admin Auto-Login</p>
                  <p className="text-xs opacity-90 text-center">
                    {adminLoginLoading 
                      ? 'Logging in as administrator... Please wait.' 
                      : adminLoginAttemptedRef.current && error
                      ? 'Auto-login failed. Click Login to retry.'
                      : 'Preparing to authenticate with admin credentials automatically in a few seconds...'}
                  </p>
                </div>
              </div>
              
              {error && (
                <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-500">
                  {error}
                </div>
              )}

              <Button
                size="lg"
                className="w-full"
                loading={adminLoginLoading || submitting}
                onClick={handleAdminAutoLogin}
                type="button"
              >
                {adminLoginLoading ? 'Logging in...' : 'Login'}
              </Button>
            </>
          ) : (
            <>
              <Input
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
              />
              <Input
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />

              {error && (
                <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-500">
                  {error}
                </div>
              )}

              <Button
                size="lg"
                className="w-full"
                loading={submitting}
                onClick={onSubmit}
                type="button"
              >
                {mode === 'login' ? 'Login' : 'Register'}
              </Button>
            </>
          )}

          {demoModeEnabled && (
            <Button
              size="lg"
              className="w-full"
              variant="secondary"
              loading={submitting}
              onClick={onDemo}
              type="button"
            >
              Continue in demo mode
            </Button>
          )}

          {role !== 'insurer' && (
            <div className="flex items-center justify-between text-sm">
              <button
                type="button"
                className="text-blue hover:text-blue-light transition-colors italic"
                onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
                disabled={submitting}
              >
                {mode === 'login' ? 'Create account' : 'I already have an account'}
              </button>
              <button
                onClick={onClose}
                className="text-blue hover:text-blue-light transition-colors italic"
              >
                Back to home
              </button>
            </div>
          )}
          {role === 'insurer' && (
            <div className="flex items-center justify-end text-sm">
              <button
                onClick={onClose}
                className="text-blue hover:text-blue-light transition-colors italic"
              >
                Back to home
              </button>
            </div>
          )}
        </div>
      </Card>

      <p className="text-xs text-blue/70 mt-6 text-center italic">
        By continuing, you agree to test in a demo environment. AI assistance may be wrong; verify before paying out.
      </p>
    </>
  );
}

export function LoginModal({ isOpen, onClose, preselectedRole = 'claimant', lockRole = false, onSuccess }: LoginModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Blurred backdrop */}
      <div 
        className="fixed inset-0 bg-black/40 backdrop-blur-md transition-opacity"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div 
          className="relative w-full max-w-lg transform transition-all"
          onClick={(e) => e.stopPropagation()}
        >
          <Suspense fallback={<div className="text-center">Loading...</div>}>
            <LoginFormContent 
              preselectedRole={preselectedRole}
              lockRole={lockRole}
              onSuccess={onSuccess}
              onClose={onClose}
            />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
