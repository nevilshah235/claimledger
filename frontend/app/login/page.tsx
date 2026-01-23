'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { Button, Card, Input } from '../components/ui';
import { useAuth } from '../providers/AuthProvider';
import { ChatAssistant } from '../components/ChatAssistant';

type Role = 'claimant' | 'insurer';

function LoginForm() {
  const searchParams = useSearchParams();
  const { user, loading, login, register, redirectToHome } = useAuth();

  const preselectedRole = useMemo<Role>(() => {
    const qp = searchParams.get('role');
    return qp === 'insurer' ? 'insurer' : 'claimant';
  }, [searchParams]);

  const [role, setRole] = useState<Role>(preselectedRole);
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const demoModeEnabled = useMemo(() => process.env.NEXT_PUBLIC_MOCK_WALLET === 'true', []);

  useEffect(() => {
    setRole(preselectedRole);
  }, [preselectedRole]);

  useEffect(() => {
    if (!loading && user) {
      redirectToHome(user.role as Role);
    }
  }, [loading, user, redirectToHome]);

  const title = mode === 'login' ? 'Welcome back' : 'Create your account';
  const subtitle =
    mode === 'login'
      ? 'Sign in to continue.'
      : 'Create an account to submit or review claims.';

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
        redirectToHome((res.role as Role) || role);
        return;
      }

      const res = await register({ email, password, role });
      redirectToHome((res.role as Role) || role);
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
      redirectToHome((res.role as Role) || role);
    } catch (e: any) {
      setError(e?.message || 'Failed to start demo mode.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="mb-8 text-center">
        <Link href="/" className="inline-flex flex-col items-center gap-0 text-blue hover:text-blue-light transition-colors">
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
        </Link>
      </div>

      <Card padding="lg">
        {/* Role toggle */}
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

        {/* Form */}
        <div className="space-y-4">
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
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
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
            Continue
          </Button>

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

          <div className="flex items-center justify-between text-sm">
            <button
              type="button"
              className="text-blue hover:text-blue-light transition-colors italic"
              onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
              disabled={submitting}
            >
              {mode === 'login' ? 'Create account' : 'I already have an account'}
            </button>
            <Link href="/" className="text-blue hover:text-blue-light transition-colors italic">
              Back to home
            </Link>
          </div>
        </div>
      </Card>

      <p className="text-xs text-blue/70 mt-6 text-center italic">
        By continuing, you agree to test in a demo environment. AI assistance may be wrong; verify before paying out.
      </p>
    </>
  );
}

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-16">
      <ChatAssistant />
      <div className="w-full max-w-lg">
        <Suspense fallback={<div className="text-white text-center">Loading...</div>}>
          <LoginForm />
        </Suspense>
      </div>
    </div>
  );
}
