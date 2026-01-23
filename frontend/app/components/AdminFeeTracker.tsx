'use client';

import { useState, useEffect } from 'react';
import { Card } from './ui';
import { api } from '@/lib/api';

interface FeeBreakdown {
  claim_id: string;
  total_cost: number;
  tool_costs: Record<string, number>;
  timestamp: string;
}

interface GasBreakdown {
  claim_id: string;
  tx_hash: string;
  gas_used: number;
  cost_arc: number;
  timestamp: string;
}

interface FeeTrackingData {
  wallet_address: string | null;
  current_balance: {
    balances: Array<{
      amount: string;
      token: {
        symbol: string;
        name?: string;
        decimals?: number;
      };
    }>;
    wallet_id?: string;
  } | null | number; // Allow number for backward compatibility, but expect the balance structure
  total_spent: number;
  total_evaluations: number;
  average_cost_per_evaluation: number;
  fee_breakdown: FeeBreakdown[];
  total_gas_arc: number;
  gas_breakdown: GasBreakdown[];
}

export function AdminFeeTracker({ refreshTrigger }: { refreshTrigger?: number }) {
  const [feeData, setFeeData] = useState<FeeTrackingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadFeeData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.admin.getFees();
      // Type assertion: API returns current_balance as Dict[str, Any] from backend,
      // but TypeScript may infer it differently. Cast to expected type.
      setFeeData(data as FeeTrackingData);
      
      // Log balance information for debugging
      if (data.current_balance === null) {
        console.warn('AdminFeeTracker: Balance is null - wallet may not be configured or balance fetch failed');
      } else {
        const usdcBalance = extractUSDCBalance(data.current_balance);
        if (usdcBalance === null) {
          console.warn('AdminFeeTracker: No USDC balance found in balance data');
        } else {
          console.info(`AdminFeeTracker: Balance loaded: ${usdcBalance} USDC`);
        }
      }
    } catch (err) {
      console.error('Failed to load fee data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load fee data');
      // Keep previous data if available, but show error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFeeData();
    // Refresh every 30 seconds
    const interval = setInterval(loadFeeData, 30000);
    return () => clearInterval(interval);
  }, []);

  // When parent increments refreshTrigger (e.g. after a settlement), refetch to show updated balance
  useEffect(() => {
    if (refreshTrigger != null && refreshTrigger > 0) loadFeeData();
  }, [refreshTrigger]);

  // Extract USDC balance from balance structure (same logic as WalletInfoModal)
  // WalletInfoModal uses parseFloat(tb.amount) directly without decimal conversion
  const extractUSDCBalance = (balance: FeeTrackingData['current_balance']): number | null => {
    // Handle case where balance might be a number (legacy format) or null
    if (balance === null || typeof balance === 'number') {
      return typeof balance === 'number' ? balance : null;
    }
    
    if (!balance.balances || balance.balances.length === 0) {
      return null;
    }
    
    // Find USDC token (USDC, USDC-TESTNET, etc.)
    const usdcToken = balance.balances.find((tb) => {
      const symbol = tb.token?.symbol?.toUpperCase() || '';
      return symbol.includes('USDC');
    });
    
    if (!usdcToken) {
      return null;
    }
    
    // Use amount directly (same as WalletInfoModal - "Show raw token amount, not decimal-adjusted")
    // The amount from Circle API is already in the correct format
    return parseFloat(usdcToken.amount || '0');
  };

  const formatCurrency = (amount: number | null) => {
    if (amount === null) return 'N/A';
    if (amount === 0) return '$0.00';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatDate = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return timestamp;
    }
  };

  if (loading && !feeData) {
    return (
      <Card className="admin-card">
        <div className="p-6">
          <div className="flex items-center justify-center py-8">
            <div className="w-6 h-6 border-2 border-blue-cobalt border-t-transparent rounded-full animate-spin" />
            <span className="ml-3 admin-text-secondary">Loading fee data...</span>
          </div>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="admin-card">
        <div className="p-6">
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3">
            <p className="text-sm text-red-400">{error}</p>
            <button
              onClick={loadFeeData}
              className="mt-2 text-xs text-red-300 hover:text-red-200 underline"
            >
              Retry
            </button>
          </div>
        </div>
      </Card>
    );
  }

  if (!feeData) {
    return null;
  }

  return (
    <Card className="admin-card">
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h2 className="text-xl font-bold admin-text-primary">Manual Payments & Usage</h2>
              <span className="px-2 py-0.5 text-xs font-medium rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">User-Controlled</span>
            </div>
            <p className="text-sm admin-text-secondary">Track usage and wallet balance for manual settlements.</p>
          </div>
          <button
            onClick={loadFeeData}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-admin-text-secondary hover:text-white transition-colors"
          >
            Refresh
          </button>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-white/5 rounded-lg p-4 border border-white/10">
            <div className="text-xs admin-text-secondary mb-1">Wallet Balance</div>
            <div className="text-xs font-medium text-cyan-400/90 mb-0.5">Your wallet (manual settlement)</div>
            <div className="text-lg font-bold admin-text-primary">
              {formatCurrency(extractUSDCBalance(feeData.current_balance))}
            </div>
          </div>

          <div className="bg-white/5 rounded-lg p-4 border border-white/10">
            <div className="text-xs admin-text-secondary mb-1">Settlement Gas</div>
            <div className="text-lg font-bold text-cyan-400">
              {(() => {
                const v = feeData.total_gas_arc ?? 0;
                return (v >= 0.0001 ? v.toFixed(6) : v.toExponential(2)) + ' ARC';
              })()}
            </div>
            <div className="text-xs admin-text-secondary mt-1">
              {(feeData.gas_breakdown ?? []).length} settlement{(feeData.gas_breakdown ?? []).length !== 1 ? 's' : ''}
            </div>
          </div>
        </div>

        {/* Settlement Gas per TX */}
        {(feeData.gas_breakdown ?? []).length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold admin-text-primary mb-3">Settlement Gas by Transaction</h3>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {(feeData.gas_breakdown ?? []).map((g) => (
                <div
                  key={g.tx_hash}
                  className="bg-white/5 rounded-lg p-3 border border-white/10"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono admin-text-secondary">
                      #{g.claim_id.slice(0, 8)}
                    </span>
                    <span className="text-xs admin-text-secondary">
                      {formatDate(g.timestamp)}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="admin-text-secondary">
                      gas: {g.gas_used.toLocaleString()}
                    </span>
                    <span className="text-cyan-400">
                      {g.cost_arc >= 0.0001 ? g.cost_arc.toFixed(6) : g.cost_arc.toExponential(2)} ARC
                    </span>
                    <a
                      href={`https://testnet.arcscan.app/tx/${g.tx_hash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-cyan-400 hover:text-cyan-300"
                    >
                      View tx
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Fee Breakdown */}
        {feeData.fee_breakdown.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold admin-text-primary mb-3">Recent Evaluations</h3>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {feeData.fee_breakdown.map((breakdown) => (
                <div
                  key={breakdown.claim_id}
                  className="bg-white/5 rounded-lg p-3 border border-white/10"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <span className="text-xs font-mono admin-text-secondary">
                        #{breakdown.claim_id.slice(0, 8)}
                      </span>
                      <span className="ml-2 text-xs admin-text-secondary">
                        {formatDate(breakdown.timestamp)}
                      </span>
                    </div>
                    <div className="text-sm font-bold admin-text-primary">
                      {formatCurrency(breakdown.total_cost)}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(breakdown.tool_costs).map(([tool, cost]) => (
                      <span
                        key={tool}
                        className="text-xs px-2 py-1 rounded bg-white/5 border border-white/10 admin-text-secondary"
                      >
                        {tool.replace('verify_', '')}: {formatCurrency(cost)}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </Card>
  );
}
