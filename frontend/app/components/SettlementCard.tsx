'use client';

import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter, Button, Badge } from './ui';
import { VerificationSteps } from './VerificationSteps';
import { Claim } from '@/lib/types';
import { api } from '@/lib/api';

interface SettlementCardProps {
  claim: Claim;
  onSettle: (claim: Claim) => void;
  settlementsEnabled?: boolean;
  onRequireEnableSettlements?: () => void;
}

export function SettlementCard({
  claim,
  onSettle,
  settlementsEnabled = true,
  onRequireEnableSettlements,
}: SettlementCardProps) {
  const [settling, setSettling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSettle = async () => {
    setSettling(true);
    setError(null);

    try {
      if (!settlementsEnabled) {
        setSettling(false);
        setError('Enable settlements to proceed.');
        onRequireEnableSettlements?.();
        return;
      }

      const result = await api.blockchain.settle(claim.id);
      
      // Fetch updated claim
      const updatedClaim = await api.claims.get(claim.id);
      onSettle(updatedClaim);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Settlement failed');
    } finally {
      setSettling(false);
    }
  };

  const formatAddress = (address: string) => {
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const canSettle = claim.status === 'APPROVED' && claim.approved_amount;

  return (
    <Card hover className="border border-white/10 admin-card">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CardTitle className="text-lg admin-text-primary">#{claim.id.slice(0, 8)}</CardTitle>
            <Badge status={claim.status} />
          </div>
          <span className="text-lg font-bold admin-text-primary">
            {formatCurrency(claim.claim_amount)}
          </span>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Claimant */}
        <div className="flex items-center justify-between text-sm">
          <span className="admin-text-secondary">Claimant</span>
          <span className="font-mono admin-text-primary">{formatAddress(claim.claimant_address)}</span>
        </div>

        {/* AI Decision */}
        {claim.decision && (
          <div className="p-3 rounded-lg bg-white/5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm admin-text-secondary">AI Decision</span>
              <span className={`text-sm font-medium ${
                claim.decision === 'APPROVED' ? 'text-emerald-400' :
                claim.decision === 'REJECTED' ? 'text-red-400' : 'text-amber-400'
              }`}>
                {claim.decision}
              </span>
            </div>
            
            {/* Confidence */}
            {claim.confidence !== null && (
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="admin-text-secondary">Confidence</span>
                  <span className="admin-text-primary">{Math.round(claim.confidence * 100)}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                  <div 
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${claim.confidence * 100}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Approved Amount */}
        {claim.approved_amount && (
          <div className="flex items-center justify-between">
            <span className="text-sm admin-text-secondary">Approved Amount</span>
            <span className="text-lg font-bold text-emerald-400">
              {formatCurrency(claim.approved_amount)} USDC
            </span>
          </div>
        )}

        {/* Transaction Hash (if settled) */}
        {claim.tx_hash && (
          <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
            <p className="text-xs text-emerald-400 mb-1">Settlement TX</p>
            <div className="flex items-center justify-between">
              <code className="text-sm font-mono text-emerald-300">
                {claim.tx_hash.slice(0, 16)}...
              </code>
              <a
                href={`https://testnet.arcscan.app/tx/${claim.tx_hash}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
              >
                Explorer
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>
          </div>
        )}

        {/* Processing Cost */}
        {claim.processing_costs && (
          <div className="flex items-center justify-between text-sm">
            <span className="admin-text-secondary">Processing Cost</span>
            <span className="text-cyan-400">{formatCurrency(claim.processing_costs)} USDC</span>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
      </CardContent>

      {/* Settle Button */}
      {canSettle && (
        <CardFooter>
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs admin-text-secondary">Settlement</span>
            <span className="text-xs px-2 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
              Network fee covered
            </span>
          </div>
          <Button
            variant="success"
            className="w-full"
            onClick={handleSettle}
            loading={settling}
          >
            {settling ? 'Processing…' : `Confirm settlement (${formatCurrency(claim.approved_amount!)} USDC)`}
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}

export default SettlementCard;
