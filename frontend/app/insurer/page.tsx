'use client';

import { useState, useEffect } from 'react';
import { Navbar } from '../components/Navbar';
import { SettlementCard } from '../components/SettlementCard';
import { Card, Button, Badge } from '../components/ui';
import { Claim } from '@/lib/types';
import { api } from '@/lib/api';

// Demo data for the insurer view
const DEMO_CLAIMS: Claim[] = [
  {
    id: 'demo-claim-001',
    claimant_address: '0xABCDEF1234567890ABCDEF1234567890ABCDEF12',
    claim_amount: 1250.00,
    status: 'APPROVED',
    decision: 'APPROVED',
    confidence: 0.92,
    approved_amount: 1250.00,
    processing_costs: 0.35,
    tx_hash: null,
    created_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // 30 min ago
  },
  {
    id: 'demo-claim-002',
    claimant_address: '0x1234567890ABCDEF1234567890ABCDEF12345678',
    claim_amount: 3500.00,
    status: 'NEEDS_REVIEW',
    decision: 'NEEDS_REVIEW',
    confidence: 0.65,
    approved_amount: null,
    processing_costs: 0.35,
    tx_hash: null,
    created_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(), // 1 hour ago
  },
  {
    id: 'demo-claim-003',
    claimant_address: '0x9876543210FEDCBA9876543210FEDCBA98765432',
    claim_amount: 750.00,
    status: 'SETTLED',
    decision: 'APPROVED',
    confidence: 0.95,
    approved_amount: 750.00,
    processing_costs: 0.35,
    tx_hash: '0x3d42c562fad62abd3bc282464cb1751845451b449b18f0c908fc2f4cd91f6811',
    created_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(), // 2 hours ago
  },
];

interface Stats {
  totalClaims: number;
  approved: number;
  settled: number;
  totalSettled: number;
}

export default function InsurerPage() {
  const [walletAddress, setWalletAddress] = useState<string | undefined>();
  const [userRole, setUserRole] = useState<string | undefined>();
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(false);
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

  const loadClaims = async () => {
    setLoading(true);
    try {
      const claimsData = await api.claims.list();
      setClaims(claimsData);
      
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
      // Fallback to demo data if not authenticated
      setClaims(DEMO_CLAIMS);
      setStats({
        totalClaims: 3,
        approved: 1,
        settled: 1,
        totalSettled: 750,
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle wallet connection
  const handleConnect = (address: string, role: string) => {
    setWalletAddress(address);
    setUserRole(role);
    loadClaims(); // Reload claims after login
  };

  // Handle wallet disconnection
  const handleDisconnect = () => {
    setWalletAddress(undefined);
    setUserRole(undefined);
    api.auth.logout();
    setClaims(DEMO_CLAIMS); // Reset to demo data
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

  // Calculate stats from claims
  useEffect(() => {
    const totalClaims = claims.length;
    const approved = claims.filter(c => c.status === 'APPROVED').length;
    const settled = claims.filter(c => c.status === 'SETTLED').length;
    const totalSettled = claims
      .filter(c => c.status === 'SETTLED' && c.approved_amount)
      .reduce((sum, c) => sum + (c.approved_amount || 0), 0);

    setStats({ totalClaims, approved, settled, totalSettled });
  }, [claims]);

  const handleSettle = (updatedClaim: Claim) => {
    setClaims(prev => prev.map(c => 
      c.id === updatedClaim.id ? updatedClaim : c
    ));
  };

  // Filter claims by status
  const pendingClaims = claims.filter(c => 
    c.status === 'APPROVED' || c.status === 'NEEDS_REVIEW'
  );
  const settledClaims = claims.filter(c => c.status === 'SETTLED');

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <div className="min-h-screen">
        <Navbar 
          walletAddress={walletAddress}
          role={userRole}
          onConnect={handleConnect}
          onDisconnect={handleDisconnect}
      />
      
      <main className="pt-24 pb-12 px-4">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="text-center mb-10">
            <h1 className="text-3xl font-bold text-white mb-2">Insurer Dashboard</h1>
            <p className="text-slate-400">Review claims and manage settlements</p>
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <Card padding="md">
              <div className="text-center">
                <div className="stat-value">{stats.totalClaims}</div>
                <div className="stat-label">Total Claims</div>
              </div>
            </Card>
            <Card padding="md">
              <div className="text-center">
                <div className="stat-value text-amber-400">{stats.approved}</div>
                <div className="stat-label">Awaiting Settlement</div>
              </div>
            </Card>
            <Card padding="md">
              <div className="text-center">
                <div className="stat-value text-emerald-400">{stats.settled}</div>
                <div className="stat-label">Settled</div>
              </div>
            </Card>
            <Card padding="md">
              <div className="text-center">
                <div className="stat-value">{formatCurrency(stats.totalSettled)}</div>
                <div className="stat-label">Total Settled</div>
              </div>
            </Card>
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
                  <p className="text-xs text-amber-400/70">Connect your wallet to settle claims</p>
                </div>
              </div>
            </Card>
          )}

          {/* Pending Claims Section */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-white">Pending Claims</h2>
              <span className="text-sm text-slate-400">{pendingClaims.length} claims</span>
            </div>
            
            {pendingClaims.length > 0 ? (
              <div className="grid md:grid-cols-2 gap-4">
                {pendingClaims.map(claim => (
                  <SettlementCard
                    key={claim.id}
                    claim={claim}
                    onSettle={handleSettle}
                  />
                ))}
              </div>
            ) : (
              <Card className="text-center py-8">
                <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <p className="text-slate-400">No pending claims</p>
              </Card>
            )}
          </div>

          {/* Settled Claims Section */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-white">Recently Settled</h2>
              <span className="text-sm text-slate-400">{settledClaims.length} claims</span>
            </div>

            {settledClaims.length > 0 ? (
              <Card padding="none">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                          Claim ID
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                          Amount
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                          Claimant
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                          Transaction
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {settledClaims.map(claim => (
                        <tr key={claim.id} className="hover:bg-white/5 transition-colors">
                          <td className="px-4 py-4 text-sm font-mono text-white">
                            #{claim.id.slice(0, 8)}
                          </td>
                          <td className="px-4 py-4 text-sm text-white font-medium">
                            {formatCurrency(claim.approved_amount || 0)} USDC
                          </td>
                          <td className="px-4 py-4 text-sm font-mono text-slate-400">
                            {claim.claimant_address.slice(0, 8)}...
                          </td>
                          <td className="px-4 py-4">
                            <Badge status={claim.status} />
                          </td>
                          <td className="px-4 py-4">
                            {claim.tx_hash && (
                              <a
                                href={`https://testnet.arcscan.app/tx/${claim.tx_hash}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
                              >
                                {claim.tx_hash.slice(0, 12)}...
                                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                </svg>
                              </a>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            ) : (
              <Card className="text-center py-8">
                <p className="text-slate-400">No settled claims yet</p>
              </Card>
            )}
          </div>

          {/* Info Section */}
          <Card className="mt-8">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">Settlement Process</h3>
                <p className="text-sm text-slate-400 mb-3">
                  When you settle a claim, the ClaimEscrow contract on Arc releases the approved 
                  USDC amount to the claimant&apos;s wallet. All transactions are recorded on-chain.
                </p>
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-slate-400">Contract:</span>
                  <code className="text-cyan-400 font-mono">0x80794995...E5d4Fa</code>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </main>
    </div>
  );
}
