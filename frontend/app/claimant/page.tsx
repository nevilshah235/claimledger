'use client';

import { useState, useEffect } from 'react';
import { Navbar } from '../components/Navbar';
import { ClaimForm } from '../components/ClaimForm';
import { ClaimStatus } from '../components/ClaimStatus';
import { Card } from '../components/ui';
import { Claim } from '@/lib/types';
import { api } from '@/lib/api';

export default function ClaimantPage() {
  const [walletAddress, setWalletAddress] = useState<string | undefined>();
  const [currentClaimId, setCurrentClaimId] = useState<string | null>(null);
  const [claim, setClaim] = useState<Claim | null>(null);
  const [loading, setLoading] = useState(false);

  // Mock wallet connection (will be replaced with Circle Wallets)
  const handleConnectWallet = () => {
    // For demo, use a mock address
    setWalletAddress('0xABCDEF1234567890ABCDEF1234567890ABCDEF12');
  };

  // Fetch claim when ID changes
  useEffect(() => {
    if (currentClaimId) {
      fetchClaim(currentClaimId);
    }
  }, [currentClaimId]);

  const fetchClaim = async (claimId: string) => {
    setLoading(true);
    try {
      const claimData = await api.claims.get(claimId);
      setClaim(claimData);
    } catch (error) {
      console.error('Failed to fetch claim:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleClaimCreated = (claimId: string) => {
    setCurrentClaimId(claimId);
  };

  const handleClaimUpdate = (updatedClaim: Claim) => {
    setClaim(updatedClaim);
  };

  return (
    <div className="min-h-screen">
      <Navbar 
        walletAddress={walletAddress}
        onConnectWallet={handleConnectWallet}
      />
      
      <main className="pt-24 pb-12 px-4">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-10">
            <h1 className="text-3xl font-bold text-white mb-2">Claimant Dashboard</h1>
            <p className="text-slate-400">Submit claims and track their status</p>
          </div>

          {/* Wallet Warning */}
          {!walletAddress && (
            <Card className="mb-6 border-amber-500/30 bg-amber-500/10">
              <div className="flex items-center gap-3">
                <svg className="w-6 h-6 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div>
                  <p className="text-sm font-medium text-amber-400">Wallet not connected</p>
                  <p className="text-xs text-amber-400/70">Connect your wallet to submit claims</p>
                </div>
              </div>
            </Card>
          )}

          <div className="grid lg:grid-cols-2 gap-6">
            {/* Submit Claim Form */}
            <div>
              <ClaimForm
                walletAddress={walletAddress}
                onClaimCreated={handleClaimCreated}
              />
            </div>

            {/* Claim Status */}
            <div>
              {loading ? (
                <Card className="h-full flex items-center justify-center min-h-[300px]">
                  <div className="text-center">
                    <svg className="w-10 h-10 text-cyan-400 animate-spin mx-auto mb-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    <p className="text-slate-400">Loading claim...</p>
                  </div>
                </Card>
              ) : claim ? (
                <ClaimStatus 
                  claim={claim}
                  onUpdate={handleClaimUpdate}
                />
              ) : (
                <Card className="h-full flex items-center justify-center min-h-[300px]">
                  <div className="text-center">
                    <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mx-auto mb-4">
                      <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <p className="text-slate-400 mb-2">No claim selected</p>
                    <p className="text-sm text-slate-500">
                      Submit a claim to see its status here
                    </p>
                  </div>
                </Card>
              )}
            </div>
          </div>

          {/* Help Section */}
          <Card className="mt-8">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">How it works</h3>
                <ol className="space-y-2 text-sm text-slate-400">
                  <li className="flex items-start gap-2">
                    <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">1</span>
                    <span>Submit your claim with the amount and evidence files</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-5 h-5 rounded-full bg-cyan-500/20 text-cyan-400 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">2</span>
                    <span>Trigger AI evaluation ($0.35 USDC in x402 micropayments)</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">3</span>
                    <span>If approved, the insurer settles your claim in USDC on Arc</span>
                  </li>
                </ol>
              </div>
            </div>
          </Card>
        </div>
      </main>
    </div>
  );
}
