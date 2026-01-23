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
        className={`w-full text-left px-3 py-2 rounded-lg border transition-all duration-200 ${
          selectedClaimant
            ? 'border-blue-cobalt bg-blue-cobalt/20'
            : 'border-white/10 bg-white/5 hover:bg-white/10 hover:border-white/20'
        }`}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium admin-text-primary">
            Claimant: {selectedLabel}
          </span>
          <svg 
            className={`w-4 h-4 opacity-80 transition-transform ${open ? 'rotate-180' : ''}`} 
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
        </div>
      </button>

      {open && (
        <div
          role="menu"
          aria-label="Claimant filter"
          className="absolute left-0 right-0 mt-2 rounded-xl border border-white/10 bg-white/10 backdrop-blur-sm shadow-lg z-50 overflow-hidden max-h-64 overflow-y-auto"
        >
          <div className="p-2">
            <button
              role="menuitem"
              onClick={() => {
                onSelect(null);
                setOpen(false);
              }}
              className={`w-full text-left rounded-lg px-3 py-2 hover:bg-white/10 transition-colors ${
                !selectedClaimant ? 'bg-blue-cobalt/20' : ''
              }`}
            >
              <div className="text-sm font-semibold admin-text-primary">All claimants</div>
              <div className="text-xs admin-text-secondary">Show all claims</div>
            </button>
            {claimants.map((address) => {
              const count = getClaimCount(address);
              return (
                <button
                  key={address}
                  role="menuitem"
                  onClick={() => {
                    onSelect(address);
                    setOpen(false);
                  }}
                  className={`w-full text-left rounded-lg px-3 py-2 hover:bg-white/10 transition-colors mt-1 ${
                    selectedClaimant === address 
                      ? 'bg-blue-cobalt/20' 
                      : ''
                  }`}
                >
                  <div className="text-sm font-semibold font-mono admin-text-primary">{formatAddress(address)}</div>
                  <div className="text-xs admin-text-secondary">{count} claim{count !== 1 ? 's' : ''}</div>
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

          {/* Fee Tracking Section */}
          <div className="mb-10">
            <AdminFeeTracker />
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
              <Card className="admin-card">
                <div className="flex items-center justify-between p-1">
                  <div>
                    <p className="text-sm font-semibold admin-text-primary">Queue</p>
                    <p className="text-xs admin-text-secondary mt-0.5">
                      {filteredClaims.length} of {claims.length} claims
                    </p>
                  </div>
                  <Button size="sm" variant="secondary" onClick={loadClaims} disabled={loadingClaims}>
                    Refresh
                  </Button>
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
                  ].map((t) => (
                    <button
                      key={t.key}
                      type="button"
                      onClick={() => setFilter(t.key as any)}
                      className={
                        filter === t.key 
                          ? 'admin-filter-button-active' 
                          : 'admin-filter-button-inactive'
                      }
                    >
                      {t.label}
                    </button>
                  ))}
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
                <Card className="py-12 text-center admin-card">
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-6 h-6 border-2 border-blue-cobalt border-t-transparent rounded-full animate-spin" />
                    <p className="admin-text-secondary text-sm">Loading claims…</p>
                  </div>
                </Card>
              ) : filteredClaims.length === 0 ? (
                <Card className="py-12 text-center admin-card">
                  <p className="admin-text-primary font-semibold mb-2">No claims</p>
                  <p className="text-sm admin-text-secondary">Nothing to review in this filter.</p>
                </Card>
              ) : (
                <div className="space-y-2.5 max-h-[calc(100vh-28rem)] overflow-y-auto pr-1">
                  {filteredClaims.map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => setSelectedClaimId(c.id)}
                      className={`w-full text-left p-3.5 rounded-xl border transition-all duration-200 backdrop-blur-sm ${
                        selectedClaimId === c.id 
                          ? 'border-blue-cobalt bg-blue-cobalt/20 shadow-lg shadow-blue-cobalt/20 scale-[1.02]' 
                          : 'border-white/10 bg-white/5 hover:bg-white/10 hover:border-white/20 hover:scale-[1.01]'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold admin-text-primary truncate">#{c.id.slice(0, 8)}</p>
                          <p className="text-xs admin-text-secondary truncate mt-0.5">{c.description || 'No description'}</p>
                        </div>
                        <div className="flex flex-col items-end shrink-0">
                          <Badge status={c.status} />
                          <span className="text-xs admin-text-secondary mt-1.5 font-medium">{formatCurrency(c.claim_amount)}</span>
                        </div>
                      </div>
                    </button>
                  ))}
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
