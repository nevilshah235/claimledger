'use client';

import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter, Button, Badge } from './ui';
import { VerificationSteps } from './VerificationSteps';
import { SummaryCard } from './SummaryCard';
import { AgentResultsBreakdown } from './AgentResultsBreakdown';
import { ReviewReasonsList } from './ReviewReasonsList';
import { EvaluationProgress } from './EvaluationProgress';
import { DataRequestCard } from './DataRequestCard';
import { ExtractedInfoSummary } from './ExtractedInfoSummary';
import { Claim, VerificationStep, EvaluationResult, AgentResult } from '@/lib/types';
import { api } from '@/lib/api';

interface ClaimStatusProps {
  claim: Claim;
  onUpdate: (claim: Claim) => void;
  autoStartEvaluation?: boolean;
}

export function ClaimStatus({ claim, onUpdate, autoStartEvaluation = false }: ClaimStatusProps) {
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'summary' | 'detailed'>('summary');
  const [evaluationResult, setEvaluationResult] = useState<EvaluationResult | null>(null);
  const [showProgress, setShowProgress] = useState(false);
  const [agentResults, setAgentResults] = useState<AgentResult[]>([]);

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
    
    // Only show steps for agents that actually ran (based on tool calls or agent results)
    if (evaluationResult?.tool_calls) {
      const toolNames = evaluationResult.tool_calls.map(tc => tc.tool_name);
      
      if (toolNames.includes('verify_document')) {
        const toolCall = evaluationResult.tool_calls.find(tc => tc.tool_name === 'verify_document');
        steps.push({
          type: 'document',
          label: 'Document',
          price: toolCall?.cost || 0.10,
          completed: isEvaluated
        });
      }
      
      if (toolNames.includes('verify_image')) {
        const toolCall = evaluationResult.tool_calls.find(tc => tc.tool_name === 'verify_image');
        steps.push({
          type: 'image',
          label: 'Image',
          price: toolCall?.cost || 0.15,
          completed: isEvaluated
        });
      }
      
      // Fraud check always runs
      if (toolNames.includes('verify_fraud')) {
        const toolCall = evaluationResult.tool_calls.find(tc => tc.tool_name === 'verify_fraud');
        steps.push({
          type: 'fraud',
          label: 'Fraud',
          price: toolCall?.cost || 0.10,
          completed: isEvaluated
        });
      }
    } else {
      // Fallback: show all steps if no tool calls available yet
      steps.push(
        { type: 'document', label: 'Document', price: 0.10, completed: isEvaluated },
        { type: 'image', label: 'Image', price: 0.15, completed: isEvaluated },
        { type: 'fraud', label: 'Fraud', price: 0.10, completed: isEvaluated }
      );
    }
    
    return steps;
  };

  // Auto-start evaluation on submit (plan requirement)
  useEffect(() => {
    if (!autoStartEvaluation) return;
    if (claim.status !== 'SUBMITTED') return;

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
        setError(err instanceof Error ? err.message : 'Evaluation failed');
        onUpdate(claim);
        setShowProgress(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoStartEvaluation, claim.id]);

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
              <span className="text-sm font-normal text-slate-300 ml-2">USDC</span>
            </p>
          </div>
          <div>
            <p className="text-sm text-slate-400">Claimant</p>
            <p className="text-sm font-mono text-white">
              {formatAddress(claim.claimant_address)}
            </p>
          </div>
        </div>

        {/* Evaluation Progress (during evaluation) */}
        {(claim.status === 'EVALUATING' || showProgress) && (
          <EvaluationProgress claimId={claim.id} onComplete={handleEvaluationComplete} />
        )}

        {/* View Toggle (when evaluated) */}
        {claim.status !== 'SUBMITTED' && claim.status !== 'EVALUATING' && (
          <div className="flex items-center gap-2 p-1 rounded-lg bg-white/5 border border-white/10 w-fit">
            <button
              onClick={() => setViewMode('summary')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                viewMode === 'summary'
                  ? 'bg-primary text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Summary
            </button>
            <button
              onClick={() => setViewMode('detailed')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                viewMode === 'detailed'
                  ? 'bg-primary text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Detailed
            </button>
          </div>
        )}

        {/* Summary View */}
        {viewMode === 'summary' && claim.status !== 'SUBMITTED' && claim.status !== 'EVALUATING' && (
          <>
            <SummaryCard
              confidence={claim.confidence}
              decision={claim.decision}
              summary={evaluationResult?.summary || null}
              approvedAmount={claim.approved_amount}
              processingCosts={claim.processing_costs}
              humanReviewRequired={claim.human_review_required}
            />

            {/* Extracted Information Summary */}
            {agentResults.length > 0 && (
              <ExtractedInfoSummary agentResults={agentResults} />
            )}

            {/* Review Reasons */}
            {(claim.decision === 'NEEDS_REVIEW' || 
              claim.decision === 'APPROVED_WITH_REVIEW' ||
              claim.human_review_required) && (
              <ReviewReasonsList
                reviewReasons={evaluationResult?.review_reasons || null}
                humanReviewRequired={claim.human_review_required}
              />
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

            {/* Tool Calls Summary */}
            {evaluationResult?.tool_calls && evaluationResult.tool_calls.length > 0 && (
              <div className="p-4 rounded-lg bg-slate-800/50">
                <p className="text-sm font-medium text-slate-400 mb-2">Tool Calls:</p>
                <div className="space-y-1">
                  {evaluationResult.tool_calls.map((toolCall, index) => (
                    <div key={index} className="flex items-center justify-between text-sm">
                      <span className="text-slate-300">
                        {toolCall.status === 'completed' && '✓ '}
                        {toolCall.tool_name}
                        {toolCall.cost !== null && toolCall.cost !== undefined && (
                          <span className="text-cyan-400 ml-2">
                            - ${toolCall.cost.toFixed(2)} USDC
                          </span>
                        )}
                      </span>
                      <span className={`text-xs ${
                        toolCall.status === 'completed' ? 'text-green-400' :
                        toolCall.status === 'pending' ? 'text-yellow-400' :
                        'text-red-400'
                      }`}>
                        {toolCall.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* Detailed View */}
        {viewMode === 'detailed' && claim.status !== 'SUBMITTED' && claim.status !== 'EVALUATING' && (
          <AgentResultsBreakdown
            claimId={claim.id}
            toolCalls={evaluationResult?.tool_calls}
          />
        )}

        {/* Data Request Card */}
        {(claim.status === 'AWAITING_DATA' || 
          claim.decision === 'NEEDS_MORE_DATA' || 
          claim.decision === 'INSUFFICIENT_DATA') && (
          <DataRequestCard
            claimId={claim.id}
            requestedData={claim.requested_data}
            onFilesUploaded={async () => {
              // Evidence uploaded triggers evaluation restart in DataRequestCard.
              // Keep progress visible and refresh claim state.
              setShowProgress(true);
              onUpdate({ ...claim, status: 'EVALUATING' as any });
            }}
          />
        )}

        {/* Verification Steps - Only show steps that were actually used */}
        {getVerificationSteps().length > 0 && (
          <VerificationSteps 
            steps={getVerificationSteps()}
            totalCost={claim.processing_costs || 0}
          />
        )}

        {/* Error */}
        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
      </CardContent>

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
