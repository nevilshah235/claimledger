'use client';

import { useState } from 'react';
import { W3SSdk } from '@circle-fin/w3s-pw-web-sdk';
import { Card, CardHeader, CardTitle, CardContent, CardFooter, Button, Badge } from './ui';
import { Claim } from '@/lib/types';
import { api } from '@/lib/api';
import { TxValidationStatus } from './TxValidationStatus';

function stepLabel(step: string): string {
  if (step === 'approve') return 'Authorize USDC for escrow';
  if (step === 'deposit') return 'Deposit to escrow';
  if (step === 'approve_claim') return 'Release to claimant';
  return step;
}

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
  const [stepper, setStepper] = useState<{
    stepIndex: number;
    totalSteps: number;
    label: string;
  } | null>(null);

  const handleSettle = async () => {
    setSettling(true);
    setError(null);
    setStepper(null);

    try {
      if (!settlementsEnabled) {
        setSettling(false);
        setError('Enable settlements to proceed.');
        onRequireEnableSettlements?.();
        return;
      }

      const init = await api.auth.circleConnectInit();
      if (!init.available || !init.app_id) {
        setError(init.message || 'Circle wallet is not available. Complete Connect in your profile.');
        setSettling(false);
        return;
      }

      const sdk = new W3SSdk({ appSettings: { appId: init.app_id } });

      let stepToRequest: 'approve' | 'deposit' | 'approve_claim' = 'approve';
      let completedCount = 0;
      let totalSteps = 3;
      let lastResult: {
        transactionId?: string;
        id?: string;
        transaction?: { id?: string };
        data?: { transactionId?: string; id?: string; transaction?: { id?: string } };
      } | null = null;
      let userToken: string | null = null;
      let encryptionKey: string | null = null;

      while (true) {
        const resp = await api.blockchain.settleChallenge(claim.id, stepToRequest);
        if (resp.user_token) userToken = resp.user_token;
        if (resp.encryption_key) encryptionKey = resp.encryption_key;
        if (userToken && encryptionKey) {
          sdk.setAuthentication({ userToken, encryptionKey });
        }

        if (completedCount === 0 && resp.step === 'deposit') totalSteps = 2;

        setStepper({
          stepIndex: completedCount + 1,
          totalSteps,
          label: stepLabel(resp.step),
        });

        const result = await new Promise<any>((resolve, reject) => {
          (sdk as any).execute(resp.challengeId, (err: any, res: any) => {
            if (err) return reject(err);
            resolve(res);
          });
        });
        lastResult = result ?? null;
        completedCount++;

        if (!resp.nextStep) break;
        stepToRequest = resp.nextStep as 'approve' | 'deposit' | 'approve_claim';
      }

      setStepper(null);

      let transactionId: string | undefined =
        lastResult?.transactionId ??
        lastResult?.data?.transactionId ??
        lastResult?.data?.transaction?.id ??
        lastResult?.transaction?.id ??
        lastResult?.id ??
        lastResult?.data?.id;

      if (!transactionId) {
        try {
          const latest = await api.blockchain.getLatestSettleTransaction(claim.id);
          transactionId = latest?.transactionId;
        } catch {
          // fallback failed; throw the original error
        }
        if (!transactionId) {
          throw new Error('Could not get transaction ID from wallet. Please try again.');
        }
      }

      await api.blockchain.settleComplete(claim.id, { transactionId });

      const updatedClaim = await api.claims.get(claim.id);
      onSettle(updatedClaim);
    } catch (err: any) {
      const msg = err?.message || '';
      const isCancel =
        /cancel/i.test(msg) || /denied/i.test(msg) || /reject/i.test(msg) || err?.code === 'USER_CANCEL';
      setError(isCancel ? 'Settlement cancelled. Claim remains approved.' : msg || 'Settlement failed.');
    } finally {
      setSettling(false);
      setStepper(null);
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
            {formatCurrency(claim.approved_amount ?? claim.claim_amount ?? 0)}
          </span>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Claimant */}
        <div className="flex items-center justify-between text-sm">
          <span className="admin-text-secondary">Claimant</span>
          <span className="font-mono admin-text-primary">{formatAddress(claim.claimant_address)}</span>
        </div>

        {/* Claimed vs Approved – make discrepancy explicit */}
        <div className="flex items-center justify-between text-sm">
          <span className="admin-text-secondary">Claimed</span>
          <span className="admin-text-primary">{formatCurrency(claim.claim_amount)} USDC</span>
        </div>

        {/* Decision: "Manual decision (override)" when insurer overrode, else "AI Decision" */}
        {claim.decision && (
          <div className="p-3 rounded-lg bg-white/5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm admin-text-secondary">
                {claim.decision_overridden ? 'Manual decision (override)' : 'AI Decision'}
              </span>
              <span className={`text-sm font-medium ${
                claim.decision === 'APPROVED' ? 'text-emerald-400' :
                claim.decision === 'REJECTED' ? 'text-red-400' : 'text-amber-400'
              }`}>
                {claim.decision}
              </span>
            </div>
            
            {/* Confidence – only for AI decisions, not manual overrides */}
            {!claim.decision_overridden && claim.confidence != null && (
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="admin-text-secondary">Confidence</span>
                  <span className="admin-text-primary">{Math.round(claim.confidence * 100)}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-slate-700 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${
                      claim.confidence >= 0.70 ? 'bg-green-500' : claim.confidence >= 0.40 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
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
            <p className="text-xs text-emerald-400 mb-1">
              {claim.auto_settled ? 'Auto-settled' : 'Settled by you'} · Settlement TX
            </p>
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
            <TxValidationStatus txHash={claim.tx_hash} className="mt-1.5" />
          </div>
        )}

        {/* Stepper (during 2–3 wallet authorizations) */}
        {stepper && (
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
            <p className="text-sm text-amber-300">
              Step {stepper.stepIndex} of {stepper.totalSteps}: {stepper.label}
            </p>
            <p className="text-xs text-amber-400/80 mt-1">Confirm in your wallet (e.g. enter PIN).</p>
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
          <p className="text-xs admin-text-secondary mb-2">
            Settle ({formatCurrency(claim.approved_amount!)} USDC). You&apos;ll be asked to authorize in your
            wallet 2–3 times (approve USDC, deposit to escrow, release to claimant).
          </p>
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
            disabled={!!stepper}
          >
            {settling && !stepper ? 'Processing…' : `Confirm settlement (${formatCurrency(claim.approved_amount!)} USDC)`}
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}

export default SettlementCard;
