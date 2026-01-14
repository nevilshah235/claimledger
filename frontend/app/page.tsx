'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Navbar } from './components/Navbar';
import { Button, Card } from './components/ui';
import { api } from '@/lib/api';

const features = [
  {
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
    title: 'AI Agent',
    subtitle: 'Powered by Gemini',
    description: 'Autonomous claim evaluation with multimodal analysis of documents and images.',
  },
  {
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    ),
    title: 'x402 Payments',
    subtitle: 'Circle Gateway',
    description: 'Real micropayments for each verification step. Pay-per-use AI services.',
  },
  {
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    title: 'USDC Settlement',
    subtitle: 'On Arc Blockchain',
    description: 'Instant, transparent settlements in USDC on the Arc blockchain network.',
  },
];

const stats = [
  { value: '$0.35', label: 'Per Claim Evaluation' },
  { value: '< 30s', label: 'Processing Time' },
  { value: '92%', label: 'AI Confidence' },
  { value: 'Instant', label: 'USDC Settlement' },
];

export default function HomePage() {
  const [walletAddress, setWalletAddress] = useState<string | undefined>();
  const [userRole, setUserRole] = useState<string | undefined>();

  // Handle wallet connection
  const handleConnect = (address: string, role: string) => {
    setWalletAddress(address);
    setUserRole(role);
  };

  // Handle wallet disconnection
  const handleDisconnect = () => {
    setWalletAddress(undefined);
    setUserRole(undefined);
    api.auth.logout();
  };

  // Restore wallet from auth on mount
  useEffect(() => {
    const loadUserInfo = async () => {
      try {
        const userInfo = await api.auth.me();
        if (userInfo.wallet_address) {
          setWalletAddress(userInfo.wallet_address);
          setUserRole(userInfo.role);
        }
      } catch (err) {
        // Not logged in
        api.auth.logout();
      }
    };
    loadUserInfo();
  }, []);

  return (
    <div className="min-h-screen">
      <Navbar 
        walletAddress={walletAddress}
        role={userRole}
        onConnect={handleConnect}
        onDisconnect={handleDisconnect}
      />
      
      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4">
        <div className="max-w-6xl mx-auto text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 mb-8">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-sm text-slate-300">Live on Arc Testnet</span>
          </div>

          {/* Title */}
          <h1 className="text-5xl md:text-7xl font-bold mb-6">
            <span className="text-white">AI-Powered</span>
            <br />
            <span className="text-gradient">Insurance Claims</span>
          </h1>

          {/* Subtitle */}
          <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-10">
            Submit claims, get instant AI evaluation, and receive USDC settlements 
            on the Arc blockchain. Transparent, fast, and trustless.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/claimant">
              <Button size="lg">
                Submit a Claim
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </Button>
            </Link>
            <Link href="/insurer">
              <Button variant="secondary" size="lg">
                View as Insurer
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-12 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {stats.map((stat, index) => (
              <Card key={index} padding="md" className="text-center">
                <div className="stat-value">{stat.value}</div>
                <div className="stat-label">{stat.label}</div>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-white mb-4">How It Works</h2>
            <p className="text-slate-400 max-w-xl mx-auto">
              Three simple steps from claim submission to USDC settlement
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <Card key={index} hover className="relative overflow-hidden">
                {/* Step number */}
                <div className="absolute top-4 right-4 w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-sm font-bold text-slate-400">
                  {index + 1}
                </div>

                {/* Icon */}
                <div className="w-14 h-14 rounded-xl gradient-hero flex items-center justify-center mb-4 text-white">
                  {feature.icon}
                </div>

                {/* Content */}
                <h3 className="text-xl font-semibold text-white mb-1">
                  {feature.title}
                </h3>
                <p className="text-sm text-cyan-400 mb-3">{feature.subtitle}</p>
                <p className="text-slate-400 text-sm leading-relaxed">
                  {feature.description}
                </p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Demo Flow Section */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto">
          <Card padding="lg">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-white mb-2">Demo Flow</h2>
              <p className="text-slate-400">Watch a claim go from submission to settlement</p>
            </div>

            {/* Flow visualization */}
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              {/* Step 1 */}
              <div className="flex-1 text-center">
                <div className="w-12 h-12 rounded-full bg-blue-500/20 border border-blue-500/50 flex items-center justify-center mx-auto mb-3">
                  <span className="text-blue-400 font-bold">1</span>
                </div>
                <p className="text-sm font-medium text-white">Submit Claim</p>
                <p className="text-xs text-slate-400">Upload evidence</p>
              </div>

              {/* Arrow */}
              <div className="hidden md:block text-slate-600">
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </div>

              {/* Step 2 */}
              <div className="flex-1 text-center">
                <div className="w-12 h-12 rounded-full bg-cyan-500/20 border border-cyan-500/50 flex items-center justify-center mx-auto mb-3">
                  <span className="text-cyan-400 font-bold">2</span>
                </div>
                <p className="text-sm font-medium text-white">AI Evaluation</p>
                <p className="text-xs text-slate-400">$0.35 in x402 fees</p>
              </div>

              {/* Arrow */}
              <div className="hidden md:block text-slate-600">
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </div>

              {/* Step 3 */}
              <div className="flex-1 text-center">
                <div className="w-12 h-12 rounded-full bg-emerald-500/20 border border-emerald-500/50 flex items-center justify-center mx-auto mb-3">
                  <span className="text-emerald-400 font-bold">3</span>
                </div>
                <p className="text-sm font-medium text-white">Settlement</p>
                <p className="text-xs text-slate-400">USDC on Arc</p>
              </div>
            </div>

            {/* CTA */}
            <div className="text-center mt-8">
              <Link href="/claimant">
                <Button>Try the Demo</Button>
              </Link>
            </div>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-4 border-t border-white/10">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded gradient-hero" />
            <span className="text-sm text-slate-400">ClaimLedger Demo</span>
          </div>
          <div className="flex items-center gap-4 text-sm text-slate-400">
            <span>Built with Google Agents Framework + Circle Gateway + Arc</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
