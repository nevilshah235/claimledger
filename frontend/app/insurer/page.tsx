'use client';

import { useMemo, useState, useEffect, useRef } from 'react';
import { Navbar } from '../components/Navbar';
import { Card, Button, Badge } from '../components/ui';
import { Claim } from '@/lib/types';
import { api } from '@/lib/api';
import { RequireRole } from '../components/RequireRole';
import { useAuth } from '../providers/AuthProvider';
import { EnableSettlementsModal, useSettlementsEnabled } from '../components/EnableSettlementsModal';
import { InsurerClaimReview } from '../components/InsurerClaimReview';
import { ChatAssistant } from '../components/ChatAssistant';
import { AdminFeeTracker } from '../components/AdminFeeTracker';
import { AutoSettleWalletCard } from '../components/AutoSettleWalletCard';
import { LoginModal } from '../components/LoginModal';

// Claimant Filter Dropdown Component
function ClaimantFilterDropdown({
  claimants,
  selectedClaimant,
  onSelect,
  formatAddress,
  claims,
}: {
  claimants: string[];
  selectedClaimant: string | null;
  onSelect: (address: string | null) => void;
  formatAddress: (address: string) => string;
  claims: Claim[];
}) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

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

  const getClaimCount = (address: string) => {
    return claims.filter((c) => c.claimant_address === address).length;
  };

  const selectedLabel = selectedClaimant 
    ? `${formatAddress(selectedClaimant)} (${getClaimCount(selectedClaimant)})`
    : 'All claimants';

  return (
    <div ref={containerRef} className="relative w-full">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`group w-full text-left px-3.5 py-2.5 rounded-lg border transition-all duration-200 flex items-center justify-between ${
          selectedClaimant
            ? 'border-blue-cobalt bg-blue-cobalt/20 text-white'
            : 'border-white/10 bg-white/5 hover:bg-white/10 hover:border-white/20 text-admin-text-primary'
        }`}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <svg className="w-4 h-4 shrink-0 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          <span className="text-sm font-medium truncate">
            {selectedClaimant ? formatAddress(selectedClaimant) : 'All claimants'}
          </span>
          {selectedClaimant && (
            <span className="text-xs opacity-70 shrink-0">
              ({getClaimCount(selectedClaimant)})
            </span>
          )}
        </div>
        <svg 
          className={`w-4 h-4 shrink-0 opacity-70 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} 
          viewBox="0 0 20 20" 
          fill="currentColor" 
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.24a.75.75 0 01-1.06 0L5.21 8.29a.75.75 0 01.02-1.08z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {open && (
        <div
          role="menu"
          aria-label="Claimant filter"
          className="absolute left-0 right-0 mt-2 rounded-xl border border-white/10 bg-white/10 backdrop-blur-sm shadow-lg z-50 overflow-hidden max-h-64 overflow-y-auto custom-scrollbar"
        >
          <div className="p-1.5">
            <button
              role="menuitem"
              onClick={() => {
                onSelect(null);
                setOpen(false);
              }}
              className={`w-full text-left rounded-lg px-3 py-2.5 hover:bg-white/10 transition-colors ${
                !selectedClaimant ? 'bg-blue-cobalt/20' : ''
              }`}
            >
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                </svg>
                <div>
                  <div className="text-sm font-semibold admin-text-primary">All claimants</div>
                  <div className="text-xs admin-text-secondary">Show all claims</div>
                </div>
              </div>
            </button>
            {claimants.map((address) => {
              const count = getClaimCount(address);
              const isSelected = selectedClaimant === address;
              return (
                <button
                  key={address}
                  role="menuitem"
                  onClick={() => {
                    onSelect(address);
                    setOpen(false);
                  }}
                  className={`w-full text-left rounded-lg px-3 py-2.5 hover:bg-white/10 transition-colors mt-1 ${
                    isSelected 
                      ? 'bg-blue-cobalt/20' 
                      : ''
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 shrink-0 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-semibold font-mono admin-text-primary truncate">{formatAddress(address)}</div>
                      <div className="text-xs admin-text-secondary">{count} claim{count !== 1 ? 's' : ''}</div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

interface Stats {
  totalClaims: number;
  approved: number;
  settled: number;
  totalSettled: number;
}

export default function InsurerPage() {
  const { walletAddress, role, logout, refresh, loading } = useAuth();
  const { enabled: settlementsEnabled } = useSettlementsEnabled();
  const [showEnableSettlements, setShowEnableSettlements] = useState(false);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loadingClaims, setLoadingClaims] = useState(false);
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'needs_review' | 'awaiting_info' | 'approved'>('all');
  const [selectedClaimant, setSelectedClaimant] = useState<string | null>(null);
  const [adminLoginAvailable, setAdminLoginAvailable] = useState(false);
  const [adminLoginLoading, setAdminLoginLoading] = useState(false);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [feeRefreshTrigger, setFeeRefreshTrigger] = useState(0);
  const [stats, setStats] = useState<Stats>({
    totalClaims: 0,
    approved: 0,
    settled: 0,
    totalSettled: 0,
  });

  // Load claims on mount
  useEffect(() => {
    loadClaims();
  }, []);

  // Show login modal when user is not logged in
  useEffect(() => {
    if (!walletAddress && !loading && !isLoginModalOpen) {
      setIsLoginModalOpen(true);
    }
  }, [walletAddress, loading, isLoginModalOpen]);

  // Handle successful login
  const handleLoginSuccess = async (address: string, userRole: string) => {
    await refresh();
    loadClaims();
    setIsLoginModalOpen(false);
  };

  // Auto-prompt after login (skippable here; hard gate is at on-chain action time)
  useEffect(() => {
    if (settlementsEnabled) return;
    setShowEnableSettlements(true);
  }, [settlementsEnabled]);

  const loadClaims = async () => {
    setLoadingClaims(true);
    try {
      const claimsData = await api.claims.list();
      setClaims(claimsData);
      if (!selectedClaimId && claimsData.length > 0) {
        setSelectedClaimId(claimsData[0].id);
      }
      
      // Calculate stats
      const approved = claimsData.filter(c => c.status === 'APPROVED' || c.status === 'SETTLED').length;
      const settled = claimsData.filter(c => c.status === 'SETTLED').length;
      const totalSettled = claimsData
        .filter(c => c.status === 'SETTLED' && c.approved_amount)
        .reduce((sum, c) => sum + (c.approved_amount || 0), 0);
      
      setStats({
        totalClaims: claimsData.length,
        approved,
        settled,
        totalSettled,
      });
    } catch (err) {
      console.error('Failed to load claims:', err);
      setClaims([]);
    } finally {
      setLoadingClaims(false);
    }
  };

  // Handle wallet connection
  const handleConnect = (address: string, role: string) => {
    refresh();
    loadClaims(); // Reload claims after login
  };

  // Handle wallet disconnection
  const handleDisconnect = () => {
    logout();
  };

  const selectedClaim = useMemo(() => {
    if (!selectedClaimId) return null;
    return claims.find((c) => c.id === selectedClaimId) || null;
  }, [claims, selectedClaimId]);

  const filteredClaims = useMemo(() => {
    let result = claims;

    // Filter by status
    if (filter === 'awaiting_info') {
      result = result.filter((c) => c.status === 'AWAITING_DATA');
    } else if (filter === 'approved') {
      result = result.filter((c) => c.status === 'APPROVED');
    } else if (filter === 'needs_review') {
      result = result.filter((c) => c.status === 'NEEDS_REVIEW' || c.human_review_required || c.decision === 'NEEDS_REVIEW');
    }
    // 'all' filter doesn't need status filtering

    // Filter by claimant
    if (selectedClaimant) {
      result = result.filter((c) => c.claimant_address === selectedClaimant);
    }

    return result;
  }, [claims, filter, selectedClaimant]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatAddress = (address: string) => {
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  };

  // Extract unique claimants from claims
  const uniqueClaimants = useMemo(() => {
    const claimants = new Set<string>();
    claims.forEach((claim) => {
      if (claim.claimant_address) {
        claimants.add(claim.claimant_address);
      }
    });
    return Array.from(claimants).sort();
  }, [claims]);

  return (
    <RequireRole role="insurer">
      <div className="admin-page min-h-screen relative">
        <EnableSettlementsModal
          isOpen={showEnableSettlements}
          onClose={() => setShowEnableSettlements(false)}
          required={false}
          role="insurer"
        />
        <LoginModal
          isOpen={isLoginModalOpen}
          onClose={() => {
            // Don't allow closing if not logged in - redirect to home instead
            if (!walletAddress) {
              window.location.href = '/';
            } else {
              setIsLoginModalOpen(false);
            }
          }}
          preselectedRole="insurer"
          lockRole={false}
          onSuccess={handleLoginSuccess}
        />
        {/* <ChatAssistant claimId={selectedClaimId} /> */}
        <Navbar 
          onConnect={handleConnect}
          onDisconnect={handleDisconnect}
        />
      
      <main className="pt-28 pb-16 px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl sm:text-5xl font-bold admin-text-primary mb-3">Administrator</h1>
            <p className="text-base sm:text-lg admin-text-secondary">Triage claims, review decisions, and settle payouts.</p>
          </div>

          {/* Admin Wallets: manual (user-controlled) + auto-settle (programmatic) */}
          <div className="mb-4">
            <h2 className="text-lg font-semibold admin-text-primary">Admin Wallets</h2>
            <p className="text-sm admin-text-secondary mt-1">
              Manual settlements use your connected wallet (user-controlled). Auto-settlements use the programmatic wallet configured on the server.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10">
            <AdminFeeTracker refreshTrigger={feeRefreshTrigger} />
            <AutoSettleWalletCard refreshTrigger={feeRefreshTrigger} />
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 mb-10">
            <Card padding="md" className="admin-card">
              <div className="text-center">
                <div className="stat-value">{stats.totalClaims}</div>
                <div className="stat-label">Total Claims</div>
              </div>
            </Card>
            <Card padding="md" className="admin-card">
              <div className="text-center">
                <div className="stat-value text-amber-400">{stats.approved}</div>
                <div className="stat-label">Approved / Settled</div>
              </div>
            </Card>
            <Card padding="md" className="admin-card">
              <div className="text-center">
                <div className="stat-value text-emerald-400">{stats.settled}</div>
                <div className="stat-label">Settled</div>
              </div>
            </Card>
            <Card padding="md" className="admin-card">
              <div className="text-center">
                <div className="stat-value">{formatCurrency(stats.totalSettled)}</div>
                <div className="stat-label">Total Settled</div>
              </div>
            </Card>
          </div>

          <div className="grid lg:grid-cols-12 gap-4 lg:gap-6">
            {/* Left: queue */}
            <div className="lg:col-span-4 space-y-4">
              {/* Queue Header */}
              <Card className="admin-card">
                <div className="flex items-start justify-between p-4 pb-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <svg className="w-5 h-5 text-blue-cobalt-light shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                      </svg>
                      <h2 className="text-base font-bold admin-text-primary">Queue</h2>
                    </div>
                    <p className="text-xs admin-text-secondary ml-7">
                      <span className="font-semibold text-white">{filteredClaims.length}</span> of <span className="font-semibold text-white">{claims.length}</span> claims
                    </p>
                  </div>
                  <button
                    onClick={loadClaims}
                    disabled={loadingClaims}
                    className="ml-3 p-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed group"
                    aria-label="Refresh claims"
                  >
                    <svg 
                      className={`w-4 h-4 admin-text-secondary group-hover:text-white transition-colors ${loadingClaims ? 'animate-spin' : ''}`}
                      fill="none" 
                      viewBox="0 0 24 24" 
                      stroke="currentColor"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </button>
                </div>
              </Card>

              {/* Filters */}
              <div className="space-y-3">
                {/* Status Filters */}
                <div className="flex flex-wrap gap-2">
                  {[
                    { key: 'all', label: 'All' },
                    { key: 'needs_review', label: 'Needs review' },
                    { key: 'awaiting_info', label: 'Awaiting info' },
                    { key: 'approved', label: 'Approved' },
                  ].map((t) => {
                    const isActive = filter === t.key;
                    return (
                      <button
                        key={t.key}
                        type="button"
                        onClick={() => setFilter(t.key as any)}
                        className={`group relative px-3.5 py-2 rounded-lg text-xs font-semibold border transition-all duration-200 ${
                          isActive
                            ? 'bg-blue-cobalt border-blue-cobalt-light text-white shadow-lg shadow-blue-cobalt/30'
                            : 'bg-white/5 border-white/15 text-admin-text-secondary hover:bg-white/10 hover:border-white/25 hover:text-white'
                        }`}
                      >
                        {isActive && (
                          <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-blue-cobalt-light/20 to-transparent pointer-events-none" />
                        )}
                        <span className="relative">{t.label}</span>
                      </button>
                    );
                  })}
                </div>

                {/* Claimant Filter */}
                {uniqueClaimants.length > 0 && (
                  <ClaimantFilterDropdown
                    claimants={uniqueClaimants}
                    selectedClaimant={selectedClaimant}
                    onSelect={setSelectedClaimant}
                    formatAddress={formatAddress}
                    claims={claims}
                  />
                )}
              </div>

              {loadingClaims ? (
                <Card className="py-16 text-center admin-card">
                  <div className="flex flex-col items-center gap-4">
                    <div className="w-8 h-8 border-3 border-blue-cobalt border-t-transparent rounded-full animate-spin" />
                    <div>
                      <p className="admin-text-primary font-medium text-sm mb-1">Loading claims</p>
                      <p className="admin-text-secondary text-xs">Please wait...</p>
                    </div>
                  </div>
                </Card>
              ) : filteredClaims.length === 0 ? (
                <Card className="py-16 text-center admin-card">
                  <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-white/5 border border-white/10 flex items-center justify-center">
                    <svg className="w-6 h-6 admin-text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <p className="admin-text-primary font-semibold mb-1.5">No claims found</p>
                  <p className="text-xs admin-text-secondary">Try adjusting your filters</p>
                </Card>
              ) : (
                <div className="space-y-2.5 max-h-[calc(100vh-28rem)] overflow-y-auto pr-1.5 custom-scrollbar">
                  {filteredClaims.map((c) => {
                    const isSelected = selectedClaimId === c.id;
                    return (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => setSelectedClaimId(c.id)}
                        className={`group w-full text-left p-4 rounded-xl border transition-all duration-200 backdrop-blur-sm relative overflow-hidden ${
                          isSelected
                            ? 'border-blue-cobalt bg-[rgba(40,52,75,0.95)] shadow-2xl shadow-blue-cobalt/50 scale-[1.01]'
                            : 'border-white/10 bg-[rgba(26,35,50,0.7)] hover:bg-[rgba(26,35,50,0.85)] hover:border-white/15 hover:scale-[1.005]'
                        }`}
                      >
                        {isSelected && (
                          <div className="absolute inset-0 bg-gradient-to-br from-blue-cobalt/20 via-blue-cobalt/10 to-transparent pointer-events-none rounded-xl" />
                        )}
                        <div className="relative flex items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 mb-1.5">
                              <span className="text-sm font-bold text-white">
                                #{c.id.slice(0, 8)}
                              </span>
                              {isSelected && (
                                <div className="w-1.5 h-1.5 rounded-full bg-blue-cobalt-light animate-pulse" />
                              )}
                            </div>
                            <p className="text-xs text-slate-300 truncate leading-relaxed">
                              {c.description || 'No description'}
                            </p>
                          </div>
                          <div className="flex flex-col items-end gap-2 shrink-0">
                            <Badge status={c.status} />
                            <div className="flex items-baseline gap-1">
                              <span className="text-sm font-bold text-white">
                                {formatCurrency(c.claim_amount)}
                              </span>
                            </div>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Right: review */}
            <div className="lg:col-span-8">
              {selectedClaim ? (
                <InsurerClaimReview
                  claim={selectedClaim}
                  onClaimUpdated={(updated) => {
                    setClaims((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
                    if (updated.status === 'SETTLED') setFeeRefreshTrigger((t) => t + 1);
                  }}
                  settlementsEnabled={settlementsEnabled}
                  onRequireEnableSettlements={() => setShowEnableSettlements(true)}
                />
              ) : (
                <Card className="h-full flex items-center justify-center min-h-[400px] admin-card">
                  <div className="text-center px-6">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-white/5 border border-white/10 flex items-center justify-center">
                      <svg className="w-8 h-8 admin-text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <p className="admin-text-primary font-semibold mb-2 text-lg">Select a claim</p>
                    <p className="text-sm admin-text-secondary">Choose a claim from the queue to review details.</p>
                  </div>
                </Card>
              )}
            </div>
          </div>
        </div>
      </main>
      </div>
    </RequireRole>
  );
}
