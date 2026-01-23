'use client';

import { useMemo, useState } from 'react';
import { Claim } from '@/lib/types';
import { api } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge, Input, Modal } from './ui';
import { AgentResultsBreakdown } from './AgentResultsBreakdown';
import { ReviewReasonsList } from './ReviewReasonsList';
import { SummaryCard } from './SummaryCard';
import { SettlementCard } from './SettlementCard';

type ViewMode = 'summary' | 'detailed';

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
  const [viewMode, setViewMode] = useState<ViewMode>('summary');
  const [actionError, setActionError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [showRequestData, setShowRequestData] = useState(false);
  const [requestedData, setRequestedData] = useState<string[]>(claim.requested_data || []);

  const [showOverride, setShowOverride] = useState(false);
  const [overrideDecision, setOverrideDecision] = useState<'APPROVED' | 'REJECTED'>('APPROVED');
  const [overrideAmount, setOverrideAmount] = useState<string>(() => String(claim.approved_amount ?? claim.claim_amount ?? ''));

  const canSettle = claim.status === 'APPROVED' && !!claim.approved_amount;

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
              {claim.description && <p className="text-sm admin-text-primary mt-3">{claim.description}</p>}
            </div>
            <div className="text-right">
              <div className="text-sm admin-text-secondary">Amount</div>
              <div className="text-xl font-bold admin-text-primary">
                ${Math.round(claim.claim_amount).toLocaleString()}
                <span className="text-sm font-normal text-blue-300 ml-2">USDC</span>
              </div>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* View toggle */}
          <div className="flex items-center gap-2 p-1 rounded-lg bg-white/5 border border-white/10 w-fit">
            <button
              onClick={() => setViewMode('summary')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                viewMode === 'summary' 
                  ? 'bg-blue-cobalt text-white shadow-lg shadow-blue-cobalt/30' 
                  : 'admin-text-secondary hover:admin-text-primary'
              }`}
            >
              Summary
            </button>
            <button
              onClick={() => setViewMode('detailed')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                viewMode === 'detailed' 
                  ? 'bg-blue-cobalt text-white shadow-lg shadow-blue-cobalt/30' 
                  : 'admin-text-secondary hover:admin-text-primary'
              }`}
            >
              Detailed
            </button>
          </div>

          {viewMode === 'summary' ? (
            <>
              <SummaryCard
                confidence={claim.confidence}
                decision={claim.decision}
                summary={null}
                approvedAmount={claim.approved_amount}
                processingCosts={claim.processing_costs}
                humanReviewRequired={claim.human_review_required}
              />

              {(claim.decision === 'NEEDS_REVIEW' ||
                claim.decision === 'APPROVED_WITH_REVIEW' ||
                claim.human_review_required) && (
                <ReviewReasonsList reviewReasons={null} humanReviewRequired={claim.human_review_required} />
              )}
            </>
          ) : (
            <AgentResultsBreakdown claimId={claim.id} />
          )}

          {actionError && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {actionError}
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

