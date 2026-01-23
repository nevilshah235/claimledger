'use client';

import { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Card } from './components/ui/Card';
import { api } from '@/lib/api';
import { ChatAssistant } from './components/ChatAssistant';
import { LoginModal } from './components/LoginModal';
import Image from 'next/image';

const features = [
  {
    icon: '/icons/gemini-logo.png',
    title: 'AI Agent',
    subtitle: 'Powered by Gemini',
    description: 'Autonomous claim evaluation with multimodal document and image analysis.',
  },
  {
    icon: '/icons/circle-logo.png',
    title: 'Circle Wallets',
    subtitle: 'Settlement & identity',
    description: 'User-controlled wallets for USDC settlements and secure sign-in.',
  },
  {
    icon: '/icons/arc-logo.png',
    title: 'USDC Settlement',
    subtitle: 'On Arc Blockchain',
    description: 'Instant, transparent settlements in USDC on the Arc blockchain network.',
  },
];

const stats = [
  { value: 'Both', label: 'Manual & Auto modes' },
  { value: '< 30s', label: 'Processing Time' },
  { value: '92%', label: 'AI Confidence' },
  { value: 'Instant', label: 'USDC Settlement' },
];

export default function HomePage() {
  const [walletAddress, setWalletAddress] = useState<string | undefined>();
  const [userRole, setUserRole] = useState<string | undefined>();
  const [revealed, setRevealed] = useState<Set<string>>(() => new Set());
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [loginModalRole, setLoginModalRole] = useState<'claimant' | 'insurer' | undefined>();

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

  // Scroll reveal for sections and staggered items
  useEffect(() => {
    const sectionEls = Array.from(document.querySelectorAll<HTMLElement>('[data-reveal-id]'));
    const staggerEls = Array.from(document.querySelectorAll<HTMLElement>('[data-stagger]'));
    
    if (sectionEls.length === 0 && staggerEls.length === 0) return;

    // Section observer with improved settings
    const sectionObs = new IntersectionObserver(
      (entries) => {
        setRevealed((prev) => {
          const next = new Set(prev);
          for (const e of entries) {
            if (e.isIntersecting) {
              const target = e.target as HTMLElement;
              next.add(target.dataset.revealId || '');
              // Remove will-change after animation completes for performance
              setTimeout(() => {
                target.style.willChange = 'auto';
              }, 1000);
            }
          }
          return next;
        });
      },
      { 
        threshold: 0.05,
        rootMargin: '0px 0px -10% 0px'
      }
    );

    // Staggered items observer
    const staggerObs = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const target = entry.target as HTMLElement;
            target.classList.add('is-visible');
            // Remove will-change after animation completes for performance
            setTimeout(() => {
              target.style.willChange = 'auto';
            }, 800);
          }
        });
      },
      { 
        threshold: 0.1,
        rootMargin: '0px 0px -5% 0px'
      }
    );

    sectionEls.forEach((el) => sectionObs.observe(el));
    staggerEls.forEach((el, index) => {
      // Add staggered delay via CSS custom property
      el.style.setProperty('--stagger-delay', `${index * 100}ms`);
      el.style.transitionDelay = `var(--stagger-delay, 0ms)`;
      staggerObs.observe(el);
    });

    return () => {
      sectionObs.disconnect();
      staggerObs.disconnect();
    };
  }, []);


  return (
    <div className="min-h-screen">
      <Navbar 
        onConnect={handleConnect}
        onDisconnect={handleDisconnect}
        onOpenLoginModal={(role) => {
          setLoginModalRole(role);
          setIsLoginModalOpen(true);
        }}
      />
      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => {
          setIsLoginModalOpen(false);
          setLoginModalRole(undefined);
        }}
        preselectedRole={loginModalRole || 'claimant'}
        lockRole={loginModalRole === 'claimant'} // Only lock when explicitly 'claimant' (from "File Claim")
        onSuccess={handleConnect}
      />
      {/* <ChatAssistant /> */}
      
      {/* Hero Section */}
      <section className="pt-28 pb-16 sm:pb-20 px-4 section-gradient-1">
        <div className="max-w-6xl mx-auto">
          <div className="text-center">
            {/* Title - with fade-in + scale effect */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-extrabold tracking-tight mb-4 leading-[1.15] headline-fade">
              <span className="text-text-primary block mb-4">You Claim, </span>
              <span className="headline-accent text-gradient-accent block">Instant Payouts</span>
            </h1>

            {/* Subtitle - just below headline */}
            <p className="text-lg sm:text-xl text-text-secondary leading-relaxed max-w-2xl mx-auto">
              Submit your claim. AI evaluates. Get paid fast.
            </p>
          </div>
        </div>
      </section>

      {/* 1-2-3 Step Framework Section */}
      <section
        id="steps"
        data-reveal-id="steps"
        className={`scroll-mt-16 py-20 px-4 section-reveal section-gradient-2 section-transition ${revealed.has('steps') ? 'is-visible' : ''}`}
      >
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight leading-snug mb-4">
              <span className="text-text-primary">Three steps to </span>
              <span className="text-gradient-accent font-extrabold">your claim</span>
            </h2>
            <p className="text-lg text-text-secondary max-w-2xl mx-auto">
              That's three steps closer to fast, secure claim processing.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                number: '1',
                title: 'Submit your claim',
                description: 'Upload your documents and claim details through our secure portal. Our system accepts photos, PDFs, and other common formats.',
                icon: '📤'
              },
              {
                number: '2',
                title: 'AI evaluation',
                description: (
                  <>
                    Our AI agents powered by <span className="highlight-term">Gemini</span> analyzes your documents, extracts key information, and evaluates your claim with audit-ready evidence.
                  </>
                ),
                icon: '🤖'
              },
              {
                number: '3',
                title: 'Instant settlement',
                description: (
                  <>
                    Get approved claims settled instantly in USDC on the <span className="highlight-term">Arc blockchain</span>. Transparent, verifiable, and secure.
                  </>
                ),
                icon: '✅'
              }
            ].map((step, index) => (
              <div
                key={index}
                data-stagger={index}
                className="stagger-item text-center"
              >
                <div className="step-number mb-4">{step.number}</div>
                <div className="text-4xl mb-4">{step.icon}</div>
                <h3 className="text-xl sm:text-2xl font-bold text-text-primary mb-3">
                  {step.title}
                </h3>
                <p className="text-base text-text-secondary leading-7">
                  {typeof step.description === 'string' ? step.description : step.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Claim Flow (Features) */}
      <section
        id="claim-flow"
        data-reveal-id="claim-flow"
        className={`scroll-mt-16 py-14 sm:py-16 px-4 section-reveal section-gradient-1 ${revealed.has('claim-flow') ? 'is-visible' : ''}`}
      >
        <div className="max-w-6xl mx-auto">
          <div className="rounded-3xl bg-white/75 backdrop-blur-[2px] border border-border shadow-sm px-6 sm:px-10 py-10">
            <div className="text-center mb-12">
              <h2 className="text-2xl sm:text-3xl font-bold tracking-tight leading-snug mb-4">
                <span className="text-text-primary">Powered by </span>
                <span className="text-gradient-primary">cutting-edge technology</span>
              </h2>
              <p className="text-base leading-7 text-text-secondary max-w-xl mx-auto">
                A clear workflow for claimants and insurers—from submission to settlement.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6" style={{ overflow: 'visible' }}>
              {features.map((feature, index) => {
                const isEven = index % 2 === 1;
                return (
                <Card 
                  key={index} 
                  hover 
                  className="relative card-enhanced stagger-item" 
                  data-stagger={index}
                  style={{ overflow: 'visible' }}
                >
                  {/* Breakout element - alternate between golden-yellow and darker navy blue */}
                  <div className={`absolute -top-4 -right-4 w-24 h-24 rounded-full blur-xl ${isEven ? 'bg-blue-cobalt/10' : 'bg-primary/10'}`} />
                  
                  {/* Icon */}
                  <div className="mb-4 flex items-center justify-start min-h-[60px] overflow-visible w-full">
                    <div className="logo-container">
                      <Image
                        src={feature.icon}
                        alt={feature.title}
                        width={220}
                        height={56}
                        className="h-14 sm:h-16 w-auto object-contain object-left logo-image"
                        style={{ maxWidth: 'none' }}
                        unoptimized
                      />
                    </div>
                  </div>

                  {/* Content */}
                  <h3 className="text-lg sm:text-xl font-semibold leading-snug text-text-primary mb-1">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-text-secondary mb-3">{feature.subtitle}</p>
                  <p className="text-sm leading-6 text-text-muted line-clamp-2">
                    {feature.description}
                  </p>
                </Card>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* Trust / Safety Section */}
      <section
        id="trust"
        data-reveal-id="trust"
        className={`scroll-mt-16 py-20 px-4 section-reveal section-gradient-trust section-transition ${revealed.has('trust') ? 'is-visible' : ''}`}
      >
        <div className="max-w-6xl mx-auto">
          <div className="rounded-3xl bg-white/85 backdrop-blur-[4px] border border-border shadow-lg px-6 sm:px-10 py-10">
            <div className="text-center mb-10">
              <h2 className="text-2xl sm:text-3xl font-bold tracking-tight leading-snug mb-3">
                <span className="text-text-primary">Built for </span>
                <span className="text-gradient-primary">trust</span>
              </h2>
              <p className="text-base leading-7 text-text-secondary max-w-2xl mx-auto">
                Audit-ready decisions, clear evidence trails, and safer payouts.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              <Card hover className="text-center card-enhanced stagger-item" data-stagger={0}>
                <div className="text-3xl mb-3">📋</div>
                <div className="text-text-primary font-semibold mb-2">Audit-ready decisions</div>
                <div className="text-sm text-text-secondary">
                  Keep a structured trail of evidence and reasoning for every claim.
                </div>
              </Card>
              <Card hover className="text-center card-enhanced stagger-item" data-stagger={1}>
                <div className="text-3xl mb-3">🔒</div>
                <div className="text-text-primary font-semibold mb-2">Payout safety</div>
                <div className="text-sm text-text-secondary">
                  On-chain settlement makes outcomes verifiable and reduces disputes.
                </div>
              </Card>
              <Card hover className="text-center card-enhanced stagger-item" data-stagger={2}>
                <div className="text-3xl mb-3">🔍</div>
                <div className="text-text-primary font-semibold mb-2">Evidence trail</div>
                <div className="text-sm text-text-secondary">
                  Collect the right documents upfront and request more when needed.
                </div>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Metrics (moved to bottom) */}
      <section
        id="metrics"
        data-reveal-id="metrics"
        className={`scroll-mt-16 py-12 px-4 section-reveal section-gradient-1 ${revealed.has('metrics') ? 'is-visible' : ''}`}
      >
        <div className="max-w-6xl mx-auto">
          <div className="rounded-3xl bg-white/75 backdrop-blur-[2px] border border-border shadow-sm px-6 sm:px-10 py-10">
            <div className="text-center mb-8">
              <h2 className="text-2xl sm:text-3xl font-bold tracking-tight leading-snug mb-3">
                <span className="text-text-primary">Performance </span>
                <span className="text-gradient-primary">metrics</span>
              </h2>
              <p className="text-base leading-7 text-text-secondary max-w-xl mx-auto">
                Key operational metrics that drive our platform
              </p>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {stats.map((stat, index) => (
                <Card key={index} padding="md" className="text-center card-enhanced stagger-item" data-stagger={index}>
                  <div className="stat-value">{stat.value}</div>
                  <div className="stat-label">{stat.label}</div>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-4 border-t border-border">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Image
              src="/uclaim-logo-transparent.png"
              alt="UClaim"
              width={240}
              height={60}
              className="h-16 w-auto"
              unoptimized
            />
            <span className="sr-only">UClaim</span>
          </div>
          <div className="flex items-center gap-4 text-sm text-text-secondary">
            <span>Fast claims. Safe payouts.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
