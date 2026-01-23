'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

type TxStatus = 'confirmed' | 'pending' | 'not_found' | 'failed' | 'unknown';

interface TxValidationStatusProps {
  txHash: string;
  className?: string;
  /** If true, show a single compact line (e.g. "✓ Confirmed"). Otherwise block + optional block #. */
  compact?: boolean;
}

export function TxValidationStatus({ txHash, className = '', compact = false }: TxValidationStatusProps) {
  const [data, setData] = useState<{
    status: TxStatus;
    block_number: number | null;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!txHash) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(false);
    api.blockchain
      .getStatus(txHash)
      .then((res) => {
        if (!cancelled) {
          setData({
            status: (res.status as TxStatus) || 'unknown',
            block_number: res.block_number ?? null,
          });
        }
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [txHash]);

  if (loading) {
    return (
      <span className={`text-xs text-slate-400 ${className}`}>
        On-chain: Checking…
      </span>
    );
  }
  if (error || !data) {
    return (
      <span className={`text-xs text-slate-500 ${className}`}>
        On-chain: Unable to verify
      </span>
    );
  }

  const { status, block_number } = data;
  const label =
    status === 'confirmed'
      ? 'Confirmed'
      : status === 'pending'
        ? 'Pending'
        : status === 'not_found'
          ? 'Not found'
          : status === 'failed'
            ? 'Failed'
            : 'Unable to verify';

  const icon = status === 'confirmed' ? '✓' : status === 'pending' ? '⋯' : status === 'failed' ? '✗' : '?';
  const color =
    status === 'confirmed'
      ? 'text-emerald-400'
      : status === 'pending'
        ? 'text-amber-400'
        : status === 'failed'
          ? 'text-red-400'
          : 'text-slate-400';

  if (compact) {
    return (
      <span className={`text-xs ${color} ${className}`}>
        On-chain: {icon} {label}
      </span>
    );
  }

  return (
    <div className={`text-xs ${className}`}>
      <span className={color}>
        On-chain: {icon} {label}
      </span>
      {status === 'confirmed' && block_number != null && (
        <span className="text-slate-500 ml-1.5">Block #{block_number.toLocaleString()}</span>
      )}
    </div>
  );
}
