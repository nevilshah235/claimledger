'use client';

import { useState, useEffect } from 'react';
import { Card } from './ui';
import { api } from '@/lib/api';
import type { AutoSettleWalletResponse } from '@/lib/types';

export function AutoSettleWalletCard({ refreshTrigger }: { refreshTrigger?: number }) {
  const [data, setData] = useState<AutoSettleWalletResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.admin.getAutoSettleWallet();
      setData(res);
    } catch (e) {
      console.error('Failed to load auto-settle wallet:', e);
      setError(e instanceof Error ? e.message : 'Failed to load auto-settle wallet');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (refreshTrigger != null && refreshTrigger > 0) load();
  }, [refreshTrigger]);

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const formatCurrency = (v: number | null | undefined) => {
    if (v == null) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(v);
  };

  // const formatEurc = (v: number | null | undefined) => {  // EURC commented out for now
  //   if (v == null) return '—';
  //   return new Intl.NumberFormat('en-US', {
  //     style: 'currency',
  //     currency: 'EUR',
  //     minimumFractionDigits: 2,
  //     maximumFractionDigits: 2,
  //   }).format(v);
  // };

  const formatGas = (v: number | null | undefined) => {
    if (v == null) return 'N/A';
    return (v >= 0.0001 ? v.toFixed(6) : v.toExponential(2)) + ' ARC';
  };

  if (loading && !data) {
    return (
      <Card className="admin-card">
        <div className="p-6">
          <div className="flex items-center justify-center py-6">
            <div className="w-5 h-5 border-2 border-blue-cobalt border-t-transparent rounded-full animate-spin" />
            <span className="ml-2 admin-text-secondary text-sm">Loading auto-settle wallet...</span>
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
            <button onClick={load} className="mt-2 text-xs text-red-300 hover:text-red-200 underline">
              Retry
            </button>
          </div>
        </div>
      </Card>
    );
  }

  if (!data) return null;

  return (
    <Card className="admin-card">
      <div className="p-6">
        <div className="flex items-center gap-2 mb-1">
          <h2 className="text-lg font-bold admin-text-primary">Auto-settle wallet</h2>
          <span className="px-2 py-0.5 text-xs font-medium rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">Programmatic</span>
        </div>

        {data.configured ? (
          <div className="space-y-3">
            {data.address && (
              <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                <div className="text-xs admin-text-secondary mb-1">Address</div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-sm font-mono admin-text-primary truncate">
                    {data.address}
                  </span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(data.address!)}
                    className="shrink-0 p-1.5 rounded bg-white/5 hover:bg-white/10 border border-white/10 text-admin-text-secondary hover:text-white transition-colors"
                    title="Copy address"
                  >
                    {copied ? (
                      <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                <div className="text-xs admin-text-secondary mb-1">USDC</div>
                <div className="text-lg font-bold admin-text-primary">
                  {formatCurrency(data.usdc_balance ?? null)}
                </div>
              </div>
              {/* EURC commented out for now
              <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                <div className="text-xs admin-text-secondary mb-1">EURC</div>
                <div className="text-lg font-bold admin-text-primary">
                  {formatEurc(data.eurc_balance ?? null)}
                </div>
              </div>
              */}
              <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                <div className="text-xs admin-text-secondary mb-1">Gas</div>
                <div className="text-lg font-bold text-cyan-400">
                  {formatGas(data.gas_balance_arc ?? null)}
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </Card>
  );
}
