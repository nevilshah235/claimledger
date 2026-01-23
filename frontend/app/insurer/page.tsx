'use client';

import { useMemo, useState, useEffect } from 'react';
import { Navbar } from '../components/Navbar';
import { Card, Button, Badge } from '../components/ui';
import { Claim } from '@/lib/types';
import { api } from '@/lib/api';
import { RequireRole } from '../components/RequireRole';
import { useAuth } from '../providers/AuthProvider';
import { EnableSettlementsModal, useSettlementsEnabled } from '../components/EnableSettlementsModal';
import { InsurerClaimReview } from '../components/InsurerClaimReview';
import { ChatAssistant } from '../components/ChatAssistant';

interface Stats {
  totalClaims: number;
  approved: number;
  settled: number;
  totalSettled: number;
}

export default function InsurerPage() {
  const { walletAddress, role, logout, refresh } = useAuth();
  const { enabled: settlementsEnabled } = useSettlementsEnabled();
  const [showEnableSettlements, setShowEnableSettlements] = useState(false);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loadingClaims, setLoadingClaims] = useState(false);
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'needs_review' | 'awaiting_info' | 'approved'>('all');
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
    if (filter === 'all') return claims;
    if (filter === 'awaiting_info') return claims.filter((c) => c.status === 'AWAITING_DATA');
    if (filter === 'approved') return claims.filter((c) => c.status === 'APPROVED');
    // needs_review
    return claims.filter((c) => c.status === 'NEEDS_REVIEW' || c.human_review_required || c.decision === 'NEEDS_REVIEW');
  }, [claims, filter]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <RequireRole role="insurer">
      <div className="admin-page min-h-screen relative">
        <EnableSettlementsModal
          isOpen={showEnableSettlements}
          onClose={() => setShowEnableSettlements(false)}
          required={false}
        />
        <ChatAssistant claimId={selectedClaimId} />
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
                    <p className="text-xs admin-text-secondary mt-0.5">{claims.length} claims</p>
                  </div>
                  <Button size="sm" variant="secondary" onClick={loadClaims} disabled={loadingClaims}>
                    Refresh
                  </Button>
                </div>
              </Card>

              {/* Filters */}
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
                      className={`w-full text-left p-3.5 rounded-xl border transition-all duration-200 admin-card ${
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
