'use client';

import { useEffect, useState } from 'react';
import { Card } from './ui';
import { EvaluationStatus } from '@/lib/types';
import { api } from '@/lib/api';

interface EvaluationProgressProps {
  claimId: string;
  onComplete?: () => void;
}

const AGENT_LABELS: Record<string, string> = {
  document: 'Document Agent',
  image: 'Image Agent',
  fraud: 'Fraud Agent',
  reasoning: 'Reasoning Agent',
  orchestrator: 'Orchestrator',
};

const AGENT_ICONS: Record<string, string> = {
  document: '📄',
  image: '🖼️',
  fraud: '🛡️',
  reasoning: '🧠',
  orchestrator: '🎯',
};

// Evaluations are free; no per-tool cost
const TOOL_COSTS: Record<string, number> = {
  verify_document: 0,
  verify_image: 0,
  verify_fraud: 0,
};

export function EvaluationProgress({ claimId, onComplete }: EvaluationProgressProps) {
  const [status, setStatus] = useState<EvaluationStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [totalCost, setTotalCost] = useState(0);

  useEffect(() => {
    if (!claimId) return;

    const pollStatus = async () => {
      try {
        const currentStatus = await api.agent.getStatus(claimId);
        setStatus(currentStatus);
        
        // Calculate total cost based on completed agents
        let cost = 0;
        if (currentStatus.completed_agents.includes('document')) cost += TOOL_COSTS.verify_document;
        if (currentStatus.completed_agents.includes('image')) cost += TOOL_COSTS.verify_image;
        if (currentStatus.completed_agents.includes('fraud')) cost += TOOL_COSTS.verify_fraud;
        setTotalCost(cost);

        // If evaluation is complete, stop polling
        if (currentStatus.status !== 'EVALUATING' && onComplete) {
          onComplete();
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch status');
      }
    };

    // Poll immediately
    pollStatus();

    // Poll every 2 seconds
    const interval = setInterval(pollStatus, 2000);

    return () => clearInterval(interval);
  }, [claimId, onComplete]);

  if (error) {
    return (
      <Card className="p-4 admin-card">
        <p className="text-sm text-red-400">{error}</p>
      </Card>
    );
  }

  if (!status) {
    return (
      <Card className="p-4 admin-card">
        <div className="animate-pulse">
          <div className="h-4 bg-slate-600 rounded w-3/4 mb-2"></div>
          <div className="h-4 bg-slate-600 rounded w-1/2"></div>
        </div>
      </Card>
    );
  }

  // Only show agents that are actually running (completed or pending)
  // Reasoning agent doesn't have a cost, so we'll show it but without cost
  const activeAgents = [
    ...status.completed_agents,
    ...status.pending_agents
  ].filter(agent => agent !== 'reasoning'); // Reasoning is shown separately
  
  // Always include reasoning if it's in the status
  const allAgents = activeAgents.length > 0 
    ? [...activeAgents, ...(status.completed_agents.includes('reasoning') || status.pending_agents.includes('reasoning') ? ['reasoning'] : [])]
    : ['document', 'image', 'fraud', 'reasoning']; // Fallback to all if no status yet
  
  return (
    <Card className="p-6 admin-card">
      <div className="mb-4">
        <h3 className="text-sm font-medium text-slate-100">Evaluation in Progress...</h3>
      </div>

      <div className="space-y-3">
        {allAgents.map((agentType) => {
          const isCompleted = status.completed_agents.includes(agentType);
          const isPending = status.pending_agents.includes(agentType);
          // Only show cost if agent actually ran (is completed or pending)
          return (
            <div
              key={agentType}
              className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50"
            >
              <div className="flex items-center gap-3">
                <span className="text-xl">{AGENT_ICONS[agentType] || '🤖'}</span>
                <div>
                  <p className="text-sm font-medium text-slate-100">
                    {AGENT_LABELS[agentType] || agentType}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {isCompleted ? (
                  <>
                    <span className="text-green-400">✓</span>
                    <span className="text-xs text-green-400 font-medium">Completed</span>
                  </>
                ) : isPending ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-cyan-400 border-t-transparent"></div>
                    <span className="text-xs text-cyan-300 font-medium">In Progress...</span>
                  </>
                ) : (
                  <>
                    <span className="text-slate-400">⏸️</span>
                    <span className="text-xs text-slate-400">Pending</span>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 text-center">
        <p className="text-xs text-slate-400">Auto-refreshing every 2s...</p>
      </div>
    </Card>
  );
}
