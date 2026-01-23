'use client';

import { useMemo, useState, useEffect, useRef } from 'react';
import { Navbar } from '../components/Navbar';
import { ClaimForm } from '../components/ClaimForm';
import { ClaimStatus } from '../components/ClaimStatus';
import { Card, Button, Badge } from '../components/ui';
import { Claim } from '@/lib/types';
import { api } from '@/lib/api';
import { RequireRole } from '../components/RequireRole';
import { useAuth } from '../providers/AuthProvider';
import { EnableSettlementsModal, useSettlementsEnabled } from '../components/EnableSettlementsModal';
import { ChatAssistant } from '../components/ChatAssistant';

export type StatusFilter = '' | 'needs_review' | 'rejected' | 'submitted' | 'approved';

const STATUS_FILTER_MAP: Record<Exclude<StatusFilter, ''>, string[]> = {
  needs_review: ['NEEDS_REVIEW', 'AWAITING_DATA'],
  rejected: ['REJECTED'],
  submitted: ['SUBMITTED', 'EVALUATING'],
  approved: ['APPROVED', 'SETTLED'],
};

export default function ClaimantPage() {
  const { walletAddress, role, logout, refresh, user, loading } = useAuth();
  const { enabled: settlementsEnabled } = useSettlementsEnabled();
  const [showEnableSettlements, setShowEnableSettlements] = useState(false);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);
  const [showNewClaim, setShowNewClaim] = useState(false);
  const [autoEvaluateClaimId, setAutoEvaluateClaimId] = useState<string | null>(null);
  const [loadingClaims, setLoadingClaims] = useState(false);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('');
  const modalShownRef = useRef(false); // Track if modal has been shown to prevent premature closing
  const modalInitializedRef = useRef(false); // Track if we've initialized the modal state
  const shouldShowModalRef = useRef(false); // Track if modal should be shown (source of truth)
  
  // Helper to check if modal should be shown from localStorage (persists across re-renders)
  const getShouldShowModalFromStorage = () => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem('should_show_enable_modal') === 'true';
  };
  
  // Helper to set modal should show in localStorage
  const setShouldShowModalInStorage = (value: boolean) => {
    if (typeof window === 'undefined') return;
    if (value) {
      localStorage.setItem('should_show_enable_modal', 'true');
    } else {
      localStorage.removeItem('should_show_enable_modal');
    }
  };

  // Listen for enable wallet flow event from WalletInfoModal
  useEffect(() => {
    const handleEnableWalletFlow = (event: Event) => {
      try {
        // Prevent event from bubbling and causing issues
        event.stopPropagation();
        
        if (!loading && user && !settlementsEnabled) {
          shouldShowModalRef.current = true;
          setShouldShowModalInStorage(true);
          setShowEnableSettlements(true);
          modalShownRef.current = true;
          modalInitializedRef.current = true;
          if (typeof window !== 'undefined') {
            localStorage.removeItem('enable_wallet_flow');
            localStorage.removeItem('uclaim_settlements_enabled');
            // Clear just_registered flag when opened from wallet flow - this is not a new registration
            localStorage.removeItem('just_registered_claimant');
          }
        }
      } catch (error) {
        // Silently handle any errors to prevent console noise
        console.warn('Error handling enableWalletFlow event:', error);
      }
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('enableWalletFlow', handleEnableWalletFlow, { passive: true });
      return () => {
        window.removeEventListener('enableWalletFlow', handleEnableWalletFlow);
      };
    }
  }, [loading, user, settlementsEnabled]);

  // Auto-prompt when settlements not enabled
  // Only run once when auth is ready - don't re-run on dependency changes
  useEffect(() => {
    // Don't show modal while auth is still loading
    if (loading) return;
    
    // Don't show modal if user is not authenticated
    if (!user) return;
    
    // Only initialize once to prevent premature closing
    if (modalInitializedRef.current) return;
    
    // Mark as initialized immediately to prevent re-runs
    modalInitializedRef.current = true;
    
    // If settlements are already enabled, don't show modal
    if (settlementsEnabled) {
      return;
    }
    
    // Check if user just registered (new user) or just logged in
    const justRegistered = typeof window !== 'undefined' && localStorage.getItem('just_registered_claimant') === 'true';
    const justLoggedIn = typeof window !== 'undefined' && localStorage.getItem('just_logged_in_claimant') === 'true';
    const enableWalletFlow = typeof window !== 'undefined' && localStorage.getItem('enable_wallet_flow') === 'true';
    
    // Show modal if settlements are not enabled AND:
    // 1. User just registered, OR
    // 2. User just logged in, OR
    // 3. Enable wallet flow was triggered, OR
    // 4. User doesn't have a wallet address
    const shouldShowModal = enableWalletFlow || justRegistered || justLoggedIn || !walletAddress;
    
    if (shouldShowModal) {
      shouldShowModalRef.current = true; // Set ref first (source of truth)
      setShouldShowModalInStorage(true); // Persist in localStorage
      setShowEnableSettlements(true);
      modalShownRef.current = true;
      
      // Clear the flags after showing modal (but keep just_registered for required check)
      if (justLoggedIn && typeof window !== 'undefined' && !justRegistered) {
        localStorage.removeItem('just_logged_in_claimant');
      }
      if (enableWalletFlow && typeof window !== 'undefined') {
        localStorage.removeItem('enable_wallet_flow');
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, user]); // Only depend on loading and user - not settlementsEnabled or walletAddress

  // Separate effect to handle settlements becoming enabled (close modal)
  // This is the ONLY place where we close the modal automatically
  useEffect(() => {
    // Only close if settlements are actually enabled AND modal should be shown
    if (settlementsEnabled && (shouldShowModalRef.current || getShouldShowModalFromStorage())) {
      shouldShowModalRef.current = false;
      setShouldShowModalInStorage(false);
      setShowEnableSettlements(false);
      modalShownRef.current = false;
      // Don't reset modalInitializedRef - user has completed setup
      if (typeof window !== 'undefined') {
        localStorage.removeItem('just_logged_in_claimant');
        localStorage.removeItem('just_registered_claimant');
        localStorage.removeItem('enable_wallet_flow');
        localStorage.removeItem('should_show_enable_modal');
      }
    }
  }, [settlementsEnabled]);

  // Sync state with ref and localStorage - these are sources of truth
  // This ensures the modal stays open once shown, even across re-renders
  // Run this check periodically to restore modal if it was closed unexpectedly
  useEffect(() => {
    if (settlementsEnabled) return; // Don't check if settlements are enabled
    
    const shouldShow = shouldShowModalRef.current || getShouldShowModalFromStorage();
    // If ref or storage says modal should be open, ensure state matches
    if (shouldShow && !showEnableSettlements) {
      setShowEnableSettlements(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settlementsEnabled]); // Only check when settlementsEnabled changes

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

  const filteredClaims = useMemo(() => {
    if (!statusFilter) return claims;
    const statuses = STATUS_FILTER_MAP[statusFilter];
    return claims.filter((c) => statuses.includes(c.status));
  }, [claims, statusFilter]);

  const selectedClaim = useMemo(() => {
    if (!selectedClaimId) return null;
    return claims.find((c) => c.id === selectedClaimId) || null;
  }, [claims, selectedClaimId]);

  return (
    <RequireRole role="claimant">
      <div className="admin-page min-h-screen relative">
        <EnableSettlementsModal
          isOpen={showEnableSettlements}
          onClose={() => {
            // Check if this is a new registration - if so, don't allow closing
            const justRegistered = typeof window !== 'undefined' && localStorage.getItem('just_registered_claimant') === 'true';
            if (justRegistered) {
              // Don't allow closing for new registrations until wallet is set up
              return;
            }
            // Only allow closing if user explicitly closes it
            shouldShowModalRef.current = false; // Update ref (source of truth)
            setShouldShowModalInStorage(false); // Clear from storage
            setShowEnableSettlements(false);
            modalShownRef.current = false;
            // Don't reset modalInitializedRef - once shown, we don't want to show it again automatically
            // Clear the flags when modal is closed
            if (typeof window !== 'undefined') {
              localStorage.removeItem('just_logged_in_claimant');
              localStorage.removeItem('just_registered_claimant');
            }
          }}
          required={typeof window !== 'undefined' && localStorage.getItem('just_registered_claimant') === 'true'}
          role="claimant"
        />
        {/* <ChatAssistant claimId={selectedClaimId} /> */}
        <Navbar
          onConnect={handleConnect}
          onDisconnect={handleDisconnect}
        />

        <main className="pt-28 pb-16 px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="max-w-6xl mx-auto">
            {/* Header */}
            <div className="text-center mb-12">
              <h1 className="text-4xl sm:text-5xl font-bold admin-text-primary mb-3">Claims</h1>
              <p className="text-base sm:text-lg admin-text-secondary">Submit a claim, track status, and respond to evidence requests.</p>
            </div>

            <div className="grid lg:grid-cols-12 gap-6">
              {/* Left: History */}
              <div className="lg:col-span-4">
                {/* Wallet Status Card */}
                {walletAddress && !settlementsEnabled && (
                  <Card className="admin-card mb-4 border-amber-500/30 bg-gradient-to-br from-amber-500/10 to-orange-500/10">
                    <div className="space-y-3">
                      <div>
                        <p className="text-sm font-semibold admin-text-primary mb-1">Enable On-Chain Payments</p>
                        <p className="text-xs admin-text-secondary">
                          Connect your wallet to receive on-chain payouts when claims are approved.
                        </p>
                      </div>
                      <Button
                        size="sm"
                        onClick={() => setShowEnableSettlements(true)}
                        className="w-full bg-gradient-to-r from-amber-400 via-yellow-400 to-orange-400 hover:from-amber-500 hover:via-yellow-500 hover:to-orange-500 text-white font-semibold shadow-lg shadow-amber-500/30"
                      >
                        <span className="mr-2">✨</span>
                        Enable Wallet
                      </Button>
                    </div>
                  </Card>
                )}
                
                <Card className="admin-card mb-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium admin-text-primary">Your claims</p>
                      <p className="text-xs admin-text-secondary">
                        {statusFilter
                          ? `${filteredClaims.length} of ${claims.length}`
                          : `${claims.length} total`}
                      </p>
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
                  {claims.length > 0 && (
                    <div className="mt-3">
                      <label htmlFor="status-filter" className="sr-only">
                        Filter by status
                      </label>
                      <select
                        id="status-filter"
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
                        className="w-full text-sm rounded-lg border border-white/20 bg-white/5 text-slate-200 px-3 py-2 focus:border-blue-cobalt focus:outline-none focus:ring-1 focus:ring-blue-cobalt"
                      >
                        <option value="">All statuses</option>
                        <option value="needs_review">Needs Review</option>
                        <option value="rejected">Rejected</option>
                        <option value="submitted">Submitted</option>
                        <option value="approved">Approved</option>
                      </select>
                    </div>
                  )}
                </Card>

                {loadingClaims ? (
                  <Card className="admin-card py-8 text-center">
                    <p className="admin-text-secondary text-sm">Loading claims…</p>
                  </Card>
                ) : claims.length === 0 ? (
                  <Card className="admin-card py-10 text-center">
                    <p className="admin-text-secondary font-medium mb-2">No claims yet</p>
                    <p className="text-sm admin-text-secondary mb-4">Submit a claim to start evaluation.</p>
                    <Button
                      onClick={() => {
                        setShowNewClaim(true);
                        setSelectedClaimId(null);
                      }}
                    >
                      Submit a claim
                    </Button>
                  </Card>
                ) : filteredClaims.length === 0 ? (
                  <Card className="admin-card py-10 text-center">
                    <p className="admin-text-secondary font-medium mb-2">No claims match this filter</p>
                    <p className="text-sm admin-text-secondary mb-4">Try “All statuses” or another status.</p>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setStatusFilter('')}
                    >
                      Clear filter
                    </Button>
                  </Card>
                ) : (
                  <div className="space-y-2">
                    {filteredClaims.map((c) => {
                      const isSelected = selectedClaimId === c.id;
                      return (
                        <button
                          key={c.id}
                          type="button"
                          onClick={() => {
                            setSelectedClaimId(c.id);
                            setShowNewClaim(false);
                          }}
                          className={`w-full text-left p-3.5 rounded-xl border transition-all duration-200 admin-card relative ${
                            isSelected
                              ? 'border-blue-cobalt bg-blue-cobalt/20 shadow-lg shadow-blue-cobalt/20 scale-[1.02]'
                              : 'border-white/10 bg-white/5 hover:bg-white/10 hover:border-white/20 hover:scale-[1.01]'
                          }`}
                        >
                          {isSelected && (
                            <div className="absolute inset-0 bg-gradient-to-br from-blue-cobalt/20 via-blue-cobalt/10 to-transparent pointer-events-none rounded-xl" />
                          )}
                          <div className="relative flex items-center justify-between gap-3">
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2">
                                <p className="text-sm font-semibold admin-text-primary truncate">#{c.id.slice(0, 8)}</p>
                                {isSelected && (
                                  <div className="w-1.5 h-1.5 rounded-full bg-blue-cobalt-light animate-pulse flex-shrink-0" />
                                )}
                              </div>
                              <p className="text-xs admin-text-secondary truncate mt-0.5">
                                {c.description || 'No description'}
                              </p>
                            </div>
                            <div className="flex flex-col items-end gap-1.5">
                              <Badge status={c.status} className="shrink-0" />
                              <span className="text-xs admin-text-secondary">
                                ${Math.round(c.claim_amount).toLocaleString()}
                              </span>
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Right: Detail */}
              <div className="lg:col-span-8">
                {showNewClaim ? (
                  <ClaimForm 
                    walletAddress={walletAddress ?? undefined} 
                    settlementsEnabled={settlementsEnabled}
                    onClaimCreated={handleClaimCreated} 
                  />
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
                    claimantView={true}
                  />
                ) : (
                  <Card className="admin-card h-full flex items-center justify-center min-h-[300px]">
                    <div className="text-center">
                      <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mx-auto mb-4">
                        <svg className="w-8 h-8 admin-text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                      <p className="admin-text-secondary mb-2">Select a claim</p>
                      <p className="text-sm admin-text-secondary">Choose a claim on the left or start a new one.</p>
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
