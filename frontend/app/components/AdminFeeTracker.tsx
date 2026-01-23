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
  } | null;
  total_spent: number;
  total_evaluations: number;
  average_cost_per_evaluation: number;
  fee_breakdown: FeeBreakdown[];
}

export function AdminFeeTracker() {
  const [feeData, setFeeData] = useState<FeeTrackingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadFeeData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.admin.getFees();
      setFeeData(data);
      
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

  // Extract USDC balance from balance structure (same logic as WalletInfoModal)
  // WalletInfoModal uses parseFloat(tb.amount) directly without decimal conversion
  const extractUSDCBalance = (balance: FeeTrackingData['current_balance']): number | null => {
    if (!balance || !balance.balances || balance.balances.length === 0) {
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
            <h2 className="text-xl font-bold admin-text-primary mb-1">AI Evaluation Fees</h2>
            <p className="text-sm admin-text-secondary">Track spending on claim evaluations</p>
          </div>
          <button
            onClick={loadFeeData}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-admin-text-secondary hover:text-white transition-colors"
          >
            Refresh
          </button>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white/5 rounded-lg p-4 border border-white/10">
            <div className="text-xs admin-text-secondary mb-1">Wallet Balance</div>
            <div className="text-lg font-bold admin-text-primary">
              {formatCurrency(extractUSDCBalance(feeData.current_balance))}
            </div>
            {feeData.wallet_address ? (
              <div className="text-xs admin-text-secondary mt-1 truncate">
                {feeData.wallet_address.slice(0, 10)}...
              </div>
            ) : (
              <div className="text-xs text-amber-400/70 mt-1">
                Wallet not configured
              </div>
            )}
            {(!feeData.current_balance || extractUSDCBalance(feeData.current_balance) === null) && (
              <div className="text-xs text-amber-400/70 mt-1">
                Balance unavailable
              </div>
            )}
          </div>

          <div className="bg-white/5 rounded-lg p-4 border border-white/10">
            <div className="text-xs admin-text-secondary mb-1">Total Spent</div>
            <div className="text-lg font-bold text-amber-400">
              {formatCurrency(feeData.total_spent)}
            </div>
            <div className="text-xs admin-text-secondary mt-1">
              {feeData.total_evaluations} evaluation{feeData.total_evaluations !== 1 ? 's' : ''}
            </div>
          </div>

          <div className="bg-white/5 rounded-lg p-4 border border-white/10">
            <div className="text-xs admin-text-secondary mb-1">Avg. per Evaluation</div>
            <div className="text-lg font-bold admin-text-primary">
              {formatCurrency(feeData.average_cost_per_evaluation)}
            </div>
            <div className="text-xs admin-text-secondary mt-1">Per claim</div>
          </div>

          <div className="bg-white/5 rounded-lg p-4 border border-white/10">
            <div className="text-xs admin-text-secondary mb-1">Total Evaluations</div>
            <div className="text-lg font-bold admin-text-primary">
              {feeData.total_evaluations}
            </div>
            <div className="text-xs admin-text-secondary mt-1">Claims processed</div>
          </div>
        </div>

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

        {feeData.fee_breakdown.length === 0 && (
          <div className="text-center py-8">
            <p className="text-sm admin-text-secondary">No evaluation fees yet</p>
            <p className="text-xs admin-text-secondary mt-1">
              Fees will appear here after claim evaluations
            </p>
          </div>
        )}
      </div>
    </Card>
  );
}
