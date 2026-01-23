'use client';

import { useState, useEffect } from 'react';
import { Modal, Button } from './ui';
import { api } from '@/lib/api';
import type { AutoSettleWalletResponse } from '@/lib/types';

interface AutoSettleWalletModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AutoSettleWalletModal({ isOpen, onClose }: AutoSettleWalletModalProps) {
  const [data, setData] = useState<AutoSettleWalletResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isOpen) {
      load();
    }
  }, [isOpen]);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.admin.getAutoSettleWallet();
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load automatic wallet');
    } finally {
      setLoading(false);
    }
  };

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

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Automatic Wallet" size="lg">
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 text-xs font-medium rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
            Programmatic
          </span>
          <span className="text-xs admin-text-secondary">
            Used when the AI auto-approves a claim. Fund with USDC and ARC.
          </span>
        </div>

        {loading && (
          <div className="flex flex-col items-center justify-center py-8 gap-3">
            <div className="w-8 h-8 border-4 border-amber-500/50 border-t-amber-400 rounded-full animate-spin" />
            <p className="text-sm admin-text-secondary">Loading automatic wallet...</p>
          </div>
        )}

        {error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30">
            <p className="text-sm text-red-400">{error}</p>
            <Button variant="secondary" size="sm" onClick={load} className="mt-3">
              Retry
            </Button>
          </div>
        )}

        {!loading && !error && data && (
          <>
            {!data.configured ? (
              <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                <p className="text-sm admin-text-primary">Not configured</p>
                {data.message && (
                  <p className="text-xs admin-text-secondary mt-1">{data.message}</p>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                {data.address && (
                  <div className="space-y-2">
                    <label className="text-xs font-semibold uppercase tracking-wide admin-text-secondary">
                      ADDRESS
                    </label>
                    <div className="flex items-center gap-2 p-3 rounded-xl bg-white/5 border border-white/10">
                      <code className="flex-1 text-sm font-mono admin-text-primary break-all">
                        {data.address}
                      </code>
                      <button
                        type="button"
                        onClick={() => copyToClipboard(data.address!)}
                        className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 transition-colors text-xs font-medium admin-text-primary"
                      >
                        {copied ? 'Copied!' : 'Copy'}
                      </button>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-xs font-semibold uppercase tracking-wide admin-text-secondary">
                      USDC BALANCE
                    </label>
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                      <span className="text-lg font-bold admin-text-primary">
                        {formatCurrency(data.usdc_balance ?? null)}
                      </span>
                    </div>
                  </div>
                  {/* EURC commented out for now
                  <div className="space-y-2">
                    <label className="text-xs font-semibold uppercase tracking-wide admin-text-secondary">
                      EURC BALANCE
                    </label>
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                      <span className="text-lg font-bold admin-text-primary">
                        {formatEurc(data.eurc_balance ?? null)}
                      </span>
                    </div>
                  </div>
                  */}
                  <div className="space-y-2">
                    <label className="text-xs font-semibold uppercase tracking-wide admin-text-secondary">
                      GAS (ARC)
                    </label>
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                      <span className="text-lg font-bold text-cyan-400">
                        {formatGas(data.gas_balance_arc ?? null)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}
