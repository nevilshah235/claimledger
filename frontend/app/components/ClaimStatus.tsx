'use client';

import { useState, useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter, Button, Badge } from './ui';
import { VerificationSteps } from './VerificationSteps';
import { SummaryCard } from './SummaryCard';
import { ReviewReasonsList } from './ReviewReasonsList';
import { EvaluationProgress } from './EvaluationProgress';
import { DataRequestCard } from './DataRequestCard';
import { ExtractedInfoSummary } from './ExtractedInfoSummary';
import { TxValidationStatus } from './TxValidationStatus';
import { Claim, VerificationStep, EvaluationResult, AgentResult } from '@/lib/types';
import { api } from '@/lib/api';

interface ClaimStatusProps {
  claim: Claim;
  onUpdate: (claim: Claim) => void;
  autoStartEvaluation?: boolean;
  /** When true, show claimant-specific copy: "You'll receive $X USDC" (APPROVED) and "You received $X USDC" (SETTLED). */
  claimantView?: boolean;
  /** Optional; called when "Refresh balance" is clicked on SETTLED (e.g. to refresh wallet balance in header). */
  onRefreshBalance?: () => void | Promise<void>;
}

export function ClaimStatus({
  claim,
  onUpdate,
  autoStartEvaluation = false,
  claimantView = false,
  onRefreshBalance,
}: ClaimStatusProps) {
  const [error, setError] = useState<string | null>(null);
  const [evaluationResult, setEvaluationResult] = useState<EvaluationResult | null>(null);
  const [showProgress, setShowProgress] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [agentResults, setAgentResults] = useState<AgentResult[]>([]);
  const evaluationStartedRef = useRef<string | null>(null); // Track which claim ID has started evaluation

  // Fetch evaluation result when claim is evaluated and we don't have it yet
  useEffect(() => {
    const shouldFetchResult = 
      claim.status !== 'SUBMITTED' && 
      claim.status !== 'EVALUATING' && 
      !evaluationResult &&
      (claim.decision || claim.confidence !== null);
    
    if (shouldFetchResult) {
      // Try to get evaluation result from agent results endpoint
      api.agent.getResults(claim.id)
        .then(() => {
          // Results exist, component will fetch them
        })
        .catch(() => {
          // Results might not exist yet, that's okay
          console.log('Agent results not available yet');
        });
    }
  }, [claim.id, claim.status, claim.decision, claim.confidence, evaluationResult]);

  // Fetch agent results for extracted info summary
  useEffect(() => {
    if (claim.status !== 'SUBMITTED' && claim.status !== 'EVALUATING') {
      api.agent.getResults(claim.id)
        .then((response) => {
          setAgentResults(response.agent_results || []);
        })
        .catch(() => {
          // Results might not exist yet, that's okay
          setAgentResults([]);
        });
    }
  }, [claim.id, claim.status]);

  // Determine verification steps based on actual agent results and status
  const getVerificationSteps = (): VerificationStep[] => {
    const isEvaluated = ['APPROVED', 'SETTLED', 'REJECTED', 'NEEDS_REVIEW', 'AWAITING_DATA'].includes(claim.status);
    
    // Get actual agent results to determine which steps were used
    const steps: VerificationStep[] = [];
    
    // Only show steps for agents that actually ran and completed successfully
    if (evaluationResult?.tool_calls && evaluationResult.tool_calls.length > 0) {
      // Only include tool calls that completed successfully
      const completedToolCalls = evaluationResult.tool_calls.filter(tc => tc.status === 'completed');
      const toolNames = completedToolCalls.map(tc => tc.tool_name);
      
      if (toolNames.includes('verify_document')) {
        const toolCall = completedToolCalls.find(tc => tc.tool_name === 'verify_document');
        steps.push({
          type: 'document',
          label: 'Document',
          price: toolCall?.cost ?? 0,
          completed: isEvaluated
        });
      }
      
      if (toolNames.includes('verify_image')) {
        const toolCall = completedToolCalls.find(tc => tc.tool_name === 'verify_image');
        steps.push({
          type: 'image',
          label: 'Image',
          price: toolCall?.cost ?? 0,
          completed: isEvaluated
        });
      }
      
      if (toolNames.includes('verify_fraud')) {
        const toolCall = completedToolCalls.find(tc => tc.tool_name === 'verify_fraud');
        steps.push({
          type: 'fraud',
          label: 'Fraud',
          price: toolCall?.cost ?? 0,
          completed: isEvaluated
        });
      }
    }
    // No fallback - only show steps that actually ran
    
    return steps;
  };

  // Auto-start evaluation on submit (plan requirement)
  useEffect(() => {
    if (!autoStartEvaluation) return;
    
    // If status is EVALUATING and we've already started evaluation, this is expected - do nothing
    if (claim.status === 'EVALUATING' && evaluationStartedRef.current === claim.id) {
      return;
    }
    
    // Only evaluate if status is SUBMITTED and we haven't already started evaluation for this claim
    if (claim.status !== 'SUBMITTED') {
      // Reset ref if status changed to something other than SUBMITTED or EVALUATING
      if (evaluationStartedRef.current === claim.id) {
        evaluationStartedRef.current = null;
      }
      return;
    }
    
    // Prevent duplicate evaluation calls for the same claim
    if (evaluationStartedRef.current === claim.id) {
      return;
    }

    // Mark that we've started evaluation for this claim
    evaluationStartedRef.current = claim.id;
    setError(null);
    setShowProgress(true);

    // Optimistically update UI
    onUpdate({ ...claim, status: 'EVALUATING' as any });

    api.agent
      .evaluate(claim.id)
      .then((result) => {
        setEvaluationResult(result);
      })
      .catch((err) => {
        // Reset ref on error so evaluation can be retried if needed
        if (evaluationStartedRef.current === claim.id) {
          evaluationStartedRef.current = null;
        }
        setError(err instanceof Error ? err.message : 'Evaluation failed');
        onUpdate(claim);
        setShowProgress(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoStartEvaluation, claim.id, claim.status]);

  const handleEvaluationComplete = async () => {
    // Refresh claim data when evaluation completes
    try {
      const updatedClaim = await api.claims.get(claim.id);
      onUpdate(updatedClaim);
      setShowProgress(false);
    } catch (err) {
      console.error('Failed to refresh claim:', err);
      setShowProgress(false);
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

  return (
    <Card className="admin-card">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-3 mb-2">
              <CardTitle className="text-lg admin-text-primary">Claim #{claim.id.slice(0, 8)}</CardTitle>
              <Badge status={claim.status} />
            </div>
            {claim.description && (
              <p className="text-xs admin-text-secondary">{claim.description}</p>
            )}
          </div>
          <div className="text-right">
            <div className="text-sm admin-text-secondary">Amount</div>
            <div className="text-xl font-bold admin-text-primary">
              {formatCurrency(claim.claim_amount || 0)}
              <span className="text-sm font-normal text-blue-300 ml-2">USDC</span>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Evaluation Progress (during evaluation) */}
        {(claim.status === 'EVALUATING' || showProgress) && (
          <>
            <EvaluationProgress claimId={claim.id} onComplete={handleEvaluationComplete} />
            {claim.status === 'EVALUATING' && claimantView && (
              <p className="text-center mt-2">
                <button
                  type="button"
                  onClick={async () => {
                    if (resetting) return;
                    setResetting(true);
                    setError(null);
                    try {
                      const updated = await api.claims.resetEvaluating(claim.id);
                      onUpdate(updated);
                      setShowProgress(false);
                      evaluationStartedRef.current = null;
                    } catch (e) {
                      setError(e instanceof Error ? e.message : 'Reset failed');
                    } finally {
                      setResetting(false);
                    }
                  }}
                  disabled={resetting}
                  className="text-xs text-cyan-400 hover:text-cyan-300 hover:underline disabled:opacity-50"
                >
                  {resetting ? 'Resetting…' : 'Stuck? Reset and try again'}
                </button>
              </p>
            )}
          </>
        )}

        {/* Summary View - Only show when claim has been evaluated */}
        {claim.status !== 'SUBMITTED' && claim.status !== 'EVALUATING' && (
          <div className="space-y-6">
            {/* Status Indicators */}
            <div className="flex flex-wrap gap-2">
              {claim.decision === 'INSUFFICIENT_DATA' || claim.decision === 'NEEDS_MORE_DATA' ? (
                <span className="px-3 py-1.5 rounded-lg bg-red-500/20 border border-red-500/50 text-red-400 text-xs font-medium">
                  Insufficient Data
                </span>
              ) : null}
              {(claim.decision === 'NEEDS_REVIEW' || claim.decision === 'APPROVED_WITH_REVIEW') && claim.human_review_required && (
                <span className="px-3 py-1.5 rounded-lg bg-amber-500/20 border border-amber-500/50 text-amber-400 text-xs font-medium">
                  Human Review Required
                </span>
              )}
            </div>

            {/* Evidence Types Requested - Show when there are requested data types or when awaiting data */}
            {(() => {
              // Get requested_data from claim or evaluation result, with fallback
              const requestedData = claim.requested_data || evaluationResult?.requested_data;
              
              // If claim is awaiting data but requested_data is empty, use default
              const isAwaitingData = claim.status === 'AWAITING_DATA' || 
                                    claim.decision === 'NEEDS_MORE_DATA' || 
                                    claim.decision === 'INSUFFICIENT_DATA';
              
              // Use requested_data if available, otherwise default to ['document', 'image'] when awaiting data
              const displayData = (requestedData && Array.isArray(requestedData) && requestedData.length > 0)
                ? requestedData
                : (isAwaitingData ? ['document', 'image'] : []);
              
              return displayData.length > 0;
            })() && (
              <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                <p className="text-xs font-medium admin-text-secondary mb-3 uppercase tracking-wide">
                  Evidence Types Requested:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {(() => {
                    const requestedData = claim.requested_data || evaluationResult?.requested_data;
                    const isAwaitingData = claim.status === 'AWAITING_DATA' || 
                                          claim.decision === 'NEEDS_MORE_DATA' || 
                                          claim.decision === 'INSUFFICIENT_DATA';
                    const displayData = (requestedData && Array.isArray(requestedData) && requestedData.length > 0)
                      ? requestedData
                      : (isAwaitingData ? ['document', 'image'] : []);
                    return displayData;
                  })().map((dataType: string) => {
                    const DATA_TYPE_LABELS: Record<string, string> = {
                      document: 'Document',
                      image: 'Image',
                      video: 'Video',
                      audio: 'Audio',
                      other: 'Other',
                    };
                    const DATA_TYPE_ICONS: Record<string, string> = {
                      document: '📄',
                      image: '🖼️',
                      video: '🎥',
                      audio: '🎵',
                      other: '📎',
                    };
                    const DATA_TYPE_DESCRIPTIONS: Record<string, string> = {
                      document: 'Invoice, receipt, or other supporting documents',
                      image: 'Photos showing damage or evidence',
                      video: 'Video evidence',
                      audio: 'Audio recordings',
                      other: 'Additional evidence',
                    };
                    return (
                      <div
                        key={dataType}
                        className="flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-white/10"
                      >
                        <span className="text-xl flex-shrink-0">
                          {DATA_TYPE_ICONS[dataType] || '📎'}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium admin-text-primary">
                            {DATA_TYPE_LABELS[dataType] || dataType.charAt(0).toUpperCase() + dataType.slice(1)}
                          </p>
                          <p className="text-xs admin-text-secondary mt-0.5">
                            {DATA_TYPE_DESCRIPTIONS[dataType] || 'Additional evidence'}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Data Request Card - Show when awaiting data */}
            {(claim.status === 'AWAITING_DATA' || 
              claim.decision === 'NEEDS_MORE_DATA' || 
              claim.decision === 'INSUFFICIENT_DATA') && (
              <DataRequestCard
                claimId={claim.id}
                requestedData={claim.requested_data}
                onFilesUploaded={async () => {
                  setShowProgress(true);
                  onUpdate({ ...claim, status: 'EVALUATING' as any });
                }}
              />
            )}

            <SummaryCard
              confidence={claim.confidence}
              decision={claim.decision}
              summary={evaluationResult?.summary || null}
              approvedAmount={claim.approved_amount}
              humanReviewRequired={!!(claim.human_review_required && (claim.decision === 'NEEDS_REVIEW' || claim.decision === 'APPROVED_WITH_REVIEW'))}
            />

            {/* Claimant: APPROVED – you'll receive $X when admin settles. Only when NOT already SETTLED. */}
            {claimantView && claim.status === 'APPROVED' && claim.approved_amount != null && (
              <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
                <p className="text-sm text-emerald-200">
                  The administrator will settle this claim. You&apos;ll receive{' '}
                  <strong>{formatCurrency(claim.approved_amount)} USDC</strong> in your wallet when
                  they do. No action needed from you.
                </p>
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      const c = await api.claims.get(claim.id);
                      onUpdate(c);
                    } catch {
                      // ignore
                    }
                  }}
                  className="mt-2 text-xs text-emerald-300 hover:text-emerald-200 transition-colors"
                >
                  Refresh status
                </button>
              </div>
            )}

            {/* Claimant: SETTLED but no tx_hash yet (e.g. DB updated to SETTLED before tx_hash) */}
            {claimantView && claim.status === 'SETTLED' && !claim.tx_hash && claim.approved_amount != null && (
              <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
                <p className="text-sm font-semibold text-emerald-300 mb-1">
                  This claim has been settled. You received{' '}
                  <strong>{formatCurrency(claim.approved_amount)} USDC</strong> in your wallet.
                </p>
                <p className="text-xs text-emerald-200/90 mb-2">It&apos;s in your wallet.</p>
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      const c = await api.claims.get(claim.id);
                      onUpdate(c);
                      await onRefreshBalance?.();
                    } catch {
                      // ignore
                    }
                  }}
                  className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
                >
                  Refresh
                </button>
              </div>
            )}

            {/* Extracted Information Summary */}
            {agentResults.length > 0 && (
              <ExtractedInfoSummary agentResults={agentResults} />
            )}

            {/* Review Reasons + Contradictions: admin only; never show to claimant */}
            {!claimantView && (claim.decision === 'NEEDS_REVIEW' || claim.decision === 'APPROVED_WITH_REVIEW') && (
              <ReviewReasonsList
                reviewReasons={evaluationResult?.review_reasons ?? claim.review_reasons ?? null}
                contradictions={evaluationResult?.contradictions ?? claim.contradictions ?? null}
                humanReviewRequired={claim.human_review_required}
              />
            )}

            {/* Settlement: claimant "You received $X" block or generic tx block */}
            {claim.tx_hash &&
              (claimantView && claim.status === 'SETTLED' ? (
                <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
                  <p className="text-sm font-semibold text-emerald-300 mb-1">
                    You received{' '}
                    {(claim.approved_amount ?? claim.claim_amount) != null
                      ? `${formatCurrency(Number(claim.approved_amount ?? claim.claim_amount))} `
                      : ''}
                    USDC
                  </p>
                  <p className="text-xs text-emerald-200/90 mb-3">It&apos;s in your wallet.</p>
                  <div className="flex flex-wrap items-center gap-2">
                    <a
                      href={`https://testnet.arcscan.app/tx/${claim.tx_hash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
                    >
                      View transaction
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                    <button
                      type="button"
                      onClick={async () => {
                        try {
                          const c = await api.claims.get(claim.id);
                          onUpdate(c);
                          await onRefreshBalance?.();
                        } catch {
                          // ignore
                        }
                      }}
                      className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
                    >
                      Refresh balance
                    </button>
                  </div>
                  <TxValidationStatus txHash={claim.tx_hash} className="mt-2" />
                </div>
              ) : (
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
                  <TxValidationStatus txHash={claim.tx_hash} className="mt-2" />
                </div>
              ))}

            {/* Verification Steps */}
            {getVerificationSteps().length > 0 && (
              <div className="space-y-2">
                <VerificationSteps 
                  steps={getVerificationSteps()}
                  totalCost={0}
                />
                {(claim.status === 'AWAITING_DATA' || 
                  claim.decision === 'NEEDS_MORE_DATA' || 
                  claim.decision === 'INSUFFICIENT_DATA') && (
                  <p className="text-xs text-slate-300 italic">
                    Initial verification steps completed, but additional evidence is needed to finalize the decision.
                  </p>
                )}
              </div>
            )}
          </div>
        )}



        {/* Error */}
        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default ClaimStatus;
