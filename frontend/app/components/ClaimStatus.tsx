'use client';

import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter, Button, Badge } from './ui';
import { VerificationSteps } from './VerificationSteps';
import { Claim, VerificationStep } from '@/lib/types';
import { api } from '@/lib/api';

interface ClaimStatusProps {
  claim: Claim;
  onUpdate: (claim: Claim) => void;
}

export function ClaimStatus({ claim, onUpdate }: ClaimStatusProps) {
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Determine verification steps based on status
  const getVerificationSteps = (): VerificationStep[] => {
    const isEvaluated = ['APPROVED', 'SETTLED', 'REJECTED', 'NEEDS_REVIEW'].includes(claim.status);
    return [
      { type: 'document', label: 'Document', price: 0.10, completed: isEvaluated },
      { type: 'image', label: 'Image', price: 0.15, completed: isEvaluated },
      { type: 'fraud', label: 'Fraud', price: 0.10, completed: isEvaluated },
    ];
  };

  const handleEvaluate = async () => {
    setEvaluating(true);
    setError(null);

    try {
      const result = await api.agent.evaluate(claim.id);
      
      // Fetch updated claim
      const updatedClaim = await api.claims.get(claim.id);
      onUpdate(updatedClaim);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Evaluation failed');
    } finally {
      setEvaluating(false);
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-4">
          <CardTitle>Claim #{claim.id.slice(0, 8)}</CardTitle>
          <Badge status={claim.status} />
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Basic Info */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-slate-400">Claim Amount</p>
            <p className="text-2xl font-bold text-white">
              {formatCurrency(claim.claim_amount)}
              <span className="text-sm font-normal text-cyan-400 ml-2">USDC</span>
            </p>
          </div>
          <div>
            <p className="text-sm text-slate-400">Claimant</p>
            <p className="text-sm font-mono text-white">
              {formatAddress(claim.claimant_address)}
            </p>
          </div>
        </div>

        {/* Verification Steps */}
        <VerificationSteps 
          steps={getVerificationSteps()}
          totalCost={claim.processing_costs || 0.35}
        />

        {/* AI Confidence (if evaluated) */}
        {claim.confidence !== null && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-slate-400">AI Confidence</span>
              <span className="text-sm font-medium text-white">
                {Math.round(claim.confidence * 100)}%
              </span>
            </div>
            <div className="confidence-meter">
              <div 
                className="confidence-fill"
                style={{ width: `${claim.confidence * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* Approved Amount (if approved) */}
        {claim.approved_amount && (
          <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
            <p className="text-sm text-emerald-400 mb-1">Approved Amount</p>
            <p className="text-xl font-bold text-emerald-400">
              {formatCurrency(claim.approved_amount)} USDC
            </p>
          </div>
        )}

        {/* Transaction Hash (if settled) */}
        {claim.tx_hash && (
          <div className="p-4 rounded-lg bg-white/5 border border-white/10">
            <p className="text-sm text-slate-400 mb-2">Settlement Transaction</p>
            <div className="flex items-center justify-between">
              <code className="text-sm font-mono text-cyan-400">
                {claim.tx_hash.slice(0, 20)}...
              </code>
              <a
                href={`https://testnet.arcscan.app/tx/${claim.tx_hash}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
              >
                View on Explorer
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {/* Processing Cost */}
        {claim.processing_costs && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-400">Total Processing Cost</span>
            <span className="font-medium text-cyan-400">
              {formatCurrency(claim.processing_costs)} USDC
            </span>
          </div>
        )}
      </CardContent>

      {/* Actions */}
      {claim.status === 'SUBMITTED' && (
        <CardFooter>
          <Button
            className="w-full"
            onClick={handleEvaluate}
            loading={evaluating}
          >
            {evaluating ? 'Evaluating...' : 'Trigger AI Evaluation'}
          </Button>
          <p className="text-xs text-slate-400 text-center mt-2">
            This will cost ~$0.35 USDC in x402 micropayments
          </p>
        </CardFooter>
      )}

      {/* Timestamp */}
      <div className="px-6 pb-4">
        <p className="text-xs text-slate-500">
          Created: {formatDate(claim.created_at)}
        </p>
      </div>
    </Card>
  );
}

export default ClaimStatus;
