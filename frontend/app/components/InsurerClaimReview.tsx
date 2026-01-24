'use client';

import { useMemo, useState, useEffect } from 'react';
import { Claim, type AgentResult } from '@/lib/types';
import { api } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge, Input, Modal } from './ui';
import { ReviewReasonsList } from './ReviewReasonsList';
import { SummaryCard } from './SummaryCard';
import { SettlementCard } from './SettlementCard';
import { EvidenceViewer } from './EvidenceViewer';
import { ExtractedInfoSummary } from './ExtractedInfoSummary';
import { TxValidationStatus } from './TxValidationStatus';

export function InsurerClaimReview({
  claim,
  onClaimUpdated,
  settlementsEnabled,
  onRequireEnableSettlements,
}: {
  claim: Claim;
  onClaimUpdated: (claim: Claim) => void;
  settlementsEnabled: boolean;
  onRequireEnableSettlements: () => void;
}) {
  const [actionError, setActionError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [showRequestData, setShowRequestData] = useState(false);
  const [requestedData, setRequestedData] = useState<string[]>(claim.requested_data || []);

  const [showOverride, setShowOverride] = useState(false);
  const [overrideDecision, setOverrideDecision] = useState<'APPROVED' | 'REJECTED'>('APPROVED');
  const [overrideAmount, setOverrideAmount] = useState<string>(() => String(claim.approved_amount ?? claim.claim_amount ?? ''));
  const [agentResults, setAgentResults] = useState<AgentResult[]>([]);

  const canSettle = claim.status === 'APPROVED' && !!claim.approved_amount;

  // Fetch agent results for extracted info summary (same as ClaimStatus)
  useEffect(() => {
    if (claim.status === 'SUBMITTED' || claim.status === 'EVALUATING') {
      setAgentResults([]);
      return;
    }
    api.agent.getResults(claim.id)
      .then((response) => {
        setAgentResults(response.agent_results || []);
      })
      .catch(() => {
        setAgentResults([]);
      });
  }, [claim.id, claim.status]);

  const statusHint = useMemo(() => {
    if (claim.status === 'AWAITING_DATA') return 'Awaiting additional evidence from claimant.';
    if (claim.status === 'NEEDS_REVIEW') return 'Manual review required.';
    if (claim.status === 'APPROVED') return 'Ready to settle.';
    if (claim.status === 'SETTLED') return 'Settlement completed.';
    return '';
  }, [claim.status]);

  const toggleRequested = (key: string) => {
    setRequestedData((prev) => (prev.includes(key) ? prev.filter((x) => x !== key) : [...prev, key]));
  };

  const submitRequestData = async () => {
    setSubmitting(true);
    setActionError(null);
    try {
      const updated = await api.claims.requestData(claim.id, requestedData);
      onClaimUpdated(updated);
      setShowRequestData(false);
    } catch (e: any) {
      setActionError(e?.message || 'Failed to request more info.');
    } finally {
      setSubmitting(false);
    }
  };

  const submitOverride = async () => {
    setSubmitting(true);
    setActionError(null);
    try {
      const approved_amount =
        overrideDecision === 'APPROVED' ? (overrideAmount ? Number(overrideAmount) : undefined) : undefined;
      const updated = await api.claims.overrideDecision(claim.id, {
        decision: overrideDecision,
        approved_amount,
      });
      onClaimUpdated(updated);
      setShowOverride(false);
    } catch (e: any) {
      setActionError(e?.message || 'Failed to override decision.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card className="admin-card">
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-3">
                <CardTitle className="text-lg admin-text-primary">Claim #{claim.id.slice(0, 8)}</CardTitle>
                <Badge status={claim.status} />
              </div>
              <p className="text-xs admin-text-secondary mt-1">{statusHint}</p>
            </div>
            <div className="text-right">
              <div className="text-sm admin-text-secondary">
                {claim.status === 'APPROVED' && claim.approved_amount != null ? 'Approved' : 'Amount'}
              </div>
              <div className="text-xl font-bold admin-text-primary">
                ${Math.round(claim.approved_amount ?? claim.claim_amount ?? 0).toLocaleString()}
                <span className="text-sm font-normal text-blue-300 ml-2">USDC</span>
              </div>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Human Input Section */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 pb-2 border-b border-blue-500/30">
              <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <h3 className="text-sm font-semibold text-blue-400 uppercase tracking-wide">Claimant Information</h3>
            </div>
            
            {/* Claim Description (Human Input) */}
            {claim.description && (
              <div className="pl-6">
                <div className="flex items-start gap-2 mb-1">
                  <span className="text-xs text-blue-300/70 font-medium">Description:</span>
                </div>
                <p className="text-sm text-blue-200 font-medium bg-blue-500/10 border border-blue-500/20 rounded-lg px-3 py-2">
                  {claim.description}
                </p>
              </div>
            )}

            {/* Evidence Files (Human Input) */}
            <div className="pl-6">
              <EvidenceViewer claimId={claim.id} />
            </div>
          </div>

          {/* AI Agent Output Section */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 pb-2 border-b border-amber-500/30">
              <svg className="w-4 h-4 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              <h3 className="text-sm font-semibold text-amber-400 uppercase tracking-wide">AI Agent Analysis</h3>
            </div>

            <SummaryCard
              confidence={claim.confidence}
              decision={claim.decision}
              summary={null}
              approvedAmount={claim.approved_amount}
              humanReviewRequired={claim.human_review_required}
            />

            {agentResults.length > 0 && (
              <ExtractedInfoSummary agentResults={agentResults} claimId={claim.id} />
            )}

            {(claim.decision === 'NEEDS_REVIEW' ||
              claim.decision === 'APPROVED_WITH_REVIEW' ||
              claim.human_review_required) && (
              <ReviewReasonsList
                reasoning={claim.reasoning ?? null}
                reviewReasons={claim.review_reasons ?? null}
                contradictions={claim.contradictions ?? null}
                humanReviewRequired={claim.human_review_required}
              />
            )}
          </div>

          {actionError && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {actionError}
            </div>
          )}

          {/* Settled: Auto-settled vs Settled by you + tx */}
          {claim.status === 'SETTLED' && (
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
              <p className="text-xs text-emerald-400 mb-1">
                {claim.auto_settled ? 'Auto-settled' : 'Settled by you'}
                {claim.tx_hash ? ' · Settlement TX' : ''}
              </p>
              {claim.tx_hash && (
                <>
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
                </>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-2">
            <Button variant="secondary" onClick={() => setShowRequestData(true)} disabled={submitting}>
              Request more info
            </Button>
            <Button onClick={() => { setOverrideDecision('APPROVED'); setShowOverride(true); }} disabled={submitting}>
              Approve (override)
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setOverrideDecision('REJECTED');
                setShowOverride(true);
              }}
              disabled={submitting}
            >
              Reject (override)
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Settlement entry point */}
      {canSettle && (
        <SettlementCard
          claim={claim}
          onSettle={onClaimUpdated}
          settlementsEnabled={settlementsEnabled}
          onRequireEnableSettlements={onRequireEnableSettlements}
        />
      )}

      {/* Request more info modal */}
      <Modal
        isOpen={showRequestData}
        onClose={() => setShowRequestData(false)}
        title="Request additional evidence"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-sm admin-text-primary">
            Select what you need. The claimant will be prompted to upload the requested evidence.
          </p>

          <div className="space-y-2">
            {['document', 'image', 'other'].map((key) => (
              <label key={key} className="flex items-center gap-2 text-sm admin-text-primary">
                <input
                  type="checkbox"
                  checked={requestedData.includes(key)}
                  onChange={() => toggleRequested(key)}
                />
                <span className="capitalize">{key}</span>
              </label>
            ))}
          </div>

          <div className="flex gap-2">
            <Button onClick={submitRequestData} loading={submitting} className="flex-1">
              Send request
            </Button>
            <Button variant="secondary" onClick={() => setShowRequestData(false)} className="flex-1">
              Cancel
            </Button>
          </div>
        </div>
      </Modal>

      {/* Override modal */}
      <Modal isOpen={showOverride} onClose={() => setShowOverride(false)} title="Override decision" size="sm">
        <div className="space-y-4">
          <p className="text-sm admin-text-primary">
            This updates the claim decision for workflow purposes.
          </p>

          {overrideDecision === 'APPROVED' && (
            <Input
              label="Approved amount (USDC)"
              type="number"
              step="0.01"
              min="0"
              value={overrideAmount}
              onChange={(e) => setOverrideAmount(e.target.value)}
            />
          )}

          <div className="flex gap-2">
            <Button onClick={submitOverride} loading={submitting} className="flex-1">
              Confirm
            </Button>
            <Button variant="secondary" onClick={() => setShowOverride(false)} className="flex-1">
              Cancel
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default InsurerClaimReview;

