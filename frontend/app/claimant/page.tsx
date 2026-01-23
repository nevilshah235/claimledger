'use client';

import { useMemo, useState, useEffect } from 'react';
import { Navbar } from '../components/Navbar';
import { ClaimForm } from '../components/ClaimForm';
import { ClaimStatus } from '../components/ClaimStatus';
import { Card, Button } from '../components/ui';
import { Claim } from '@/lib/types';
import { api } from '@/lib/api';
import { RequireRole } from '../components/RequireRole';
import { useAuth } from '../providers/AuthProvider';
import { EnableSettlementsModal, useSettlementsEnabled } from '../components/EnableSettlementsModal';
import { ChatAssistant } from '../components/ChatAssistant';

export default function ClaimantPage() {
  const { walletAddress, role, logout, refresh } = useAuth();
  const { enabled: settlementsEnabled } = useSettlementsEnabled();
  const [showEnableSettlements, setShowEnableSettlements] = useState(false);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);
  const [showNewClaim, setShowNewClaim] = useState(false);
  const [autoEvaluateClaimId, setAutoEvaluateClaimId] = useState<string | null>(null);
  const [loadingClaims, setLoadingClaims] = useState(false);

  // Auto-prompt after login (skippable; off-chain features still work)
  useEffect(() => {
    if (settlementsEnabled) return;
    setShowEnableSettlements(true);
  }, [settlementsEnabled]);

  // Handle wallet connection
  const handleConnect = (address: string, role: string) => {
    // AuthModal/legacy flow may set localStorage; refresh canonical auth state
    refresh();
  };

  // Handle wallet disconnection
  const handleDisconnect = () => {
    logout();
  };

  const loadClaims = async (selectFirst = false) => {
    setLoadingClaims(true);
    try {
      const list = await api.claims.list();
      setClaims(list);
      if (selectFirst && list.length > 0) {
        setSelectedClaimId(list[0].id);
      }
    } catch (e) {
      console.error('Failed to load claims:', e);
      setClaims([]);
    } finally {
      setLoadingClaims(false);
    }
  };

  useEffect(() => {
    loadClaims(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleClaimCreated = (claimId: string) => {
    setShowNewClaim(false);
    setSelectedClaimId(claimId);
    setAutoEvaluateClaimId(claimId);
    // Refresh list so the new claim appears in history
    loadClaims(false);
  };

  const handleClaimUpdate = (updatedClaim: Claim) => {
    setClaims((prev) => prev.map((c) => (c.id === updatedClaim.id ? updatedClaim : c)));
  };

  const selectedClaim = useMemo(() => {
    if (!selectedClaimId) return null;
    return claims.find((c) => c.id === selectedClaimId) || null;
  }, [claims, selectedClaimId]);

  const statusLabel = (c: Claim) => {
    switch (c.status) {
      case 'SUBMITTED':
        return 'Submitted';
      case 'EVALUATING':
        return 'In review';
      case 'AWAITING_DATA':
        return 'Needs info';
      case 'NEEDS_REVIEW':
        return 'Needs manual review';
      case 'APPROVED':
        return 'Approved';
      case 'SETTLED':
        return 'Settled';
      case 'REJECTED':
        return 'Rejected';
      default:
        return c.status;
    }
  };

  return (
    <RequireRole role="claimant">
      <div className="min-h-screen">
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

        <main className="pt-24 pb-12 px-4">
          <div className="max-w-6xl mx-auto">
            {/* Header */}
            <div className="text-center mb-10">
              <h1 className="text-3xl font-bold text-white mb-2">Claims</h1>
              <p className="text-slate-400">Submit a claim, track status, and respond to evidence requests.</p>
            </div>

            <div className="grid lg:grid-cols-12 gap-6">
              {/* Left: History */}
              <div className="lg:col-span-4">
                <Card className="mb-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-white">Your claims</p>
                      <p className="text-xs text-slate-400">{claims.length} total</p>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => {
                        setShowNewClaim(true);
                        setSelectedClaimId(null);
                      }}
                    >
                      New claim
                    </Button>
                  </div>
                </Card>

                {loadingClaims ? (
                  <Card className="py-8 text-center">
                    <p className="text-slate-400 text-sm">Loading claims…</p>
                  </Card>
                ) : claims.length === 0 ? (
                  <Card className="py-10 text-center">
                    <p className="text-slate-300 font-medium mb-2">No claims yet</p>
                    <p className="text-sm text-slate-500 mb-4">Submit a claim to start evaluation.</p>
                    <Button
                      onClick={() => {
                        setShowNewClaim(true);
                        setSelectedClaimId(null);
                      }}
                    >
                      Submit a claim
                    </Button>
                  </Card>
                ) : (
                  <div className="space-y-2">
                    {claims.map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => {
                          setSelectedClaimId(c.id);
                          setShowNewClaim(false);
                        }}
                        className={`w-full text-left p-3 rounded-xl border transition-colors ${
                          selectedClaimId === c.id
                            ? 'border-cyan-500/40 bg-cyan-500/10'
                            : 'border-white/10 bg-white/5 hover:bg-white/10'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div className="min-w-0">
                            <p className="text-sm font-semibold text-white truncate">#{c.id.slice(0, 8)}</p>
                            <p className="text-xs text-slate-400 truncate">
                              {c.description || 'No description'}
                            </p>
                          </div>
                          <div className="flex flex-col items-end">
                            <span className="text-xs text-slate-300">{statusLabel(c)}</span>
                            <span className="text-xs text-slate-500">
                              ${Math.round(c.claim_amount).toLocaleString()}
                            </span>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Right: Detail */}
              <div className="lg:col-span-8">
                {showNewClaim ? (
                  <ClaimForm walletAddress={walletAddress ?? undefined} onClaimCreated={handleClaimCreated} />
                ) : selectedClaim ? (
                  <ClaimStatus
                    claim={selectedClaim}
                    onUpdate={(updated) => {
                      handleClaimUpdate(updated);
                      if (autoEvaluateClaimId === updated.id && updated.status === 'EVALUATING') {
                        setAutoEvaluateClaimId(null);
                      }
                    }}
                    autoStartEvaluation={selectedClaim.id === autoEvaluateClaimId}
                  />
                ) : (
                  <Card className="h-full flex items-center justify-center min-h-[300px]">
                    <div className="text-center">
                      <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mx-auto mb-4">
                        <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                      <p className="text-slate-400 mb-2">Select a claim</p>
                      <p className="text-sm text-slate-500">Choose a claim on the left or start a new one.</p>
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
