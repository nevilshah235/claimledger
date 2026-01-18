'use client';

import { useEffect, useState } from 'react';
import { Card } from './ui';
import { EvaluationStatus, AgentLog } from '@/lib/types';
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

const TOOL_COSTS: Record<string, number> = {
  verify_document: 0.10,
  verify_image: 0.15,
  verify_fraud: 0.10,
};

export function EvaluationProgress({ claimId, onComplete }: EvaluationProgressProps) {
  const [status, setStatus] = useState<EvaluationStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [totalCost, setTotalCost] = useState(0);
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const [showLogs, setShowLogs] = useState(true);

  useEffect(() => {
    if (!claimId) return;

    const pollStatus = async () => {
      try {
        const [currentStatus, logsResponse] = await Promise.all([
          api.agent.getStatus(claimId),
          api.agent.getLogs(claimId).catch((err) => {
            // Log error but don't fail - logs are optional
            console.warn('Failed to fetch agent logs:', err);
            return { logs: [] };
          })
        ]);
        
        setStatus(currentStatus);
        const fetchedLogs = logsResponse?.logs || [];
        setLogs(fetchedLogs);
        
        // Debug: log if we got logs
        if (fetchedLogs.length > 0) {
          console.log(`Fetched ${fetchedLogs.length} agent logs`);
        }
        
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
      <Card className="p-4">
        <p className="text-sm text-red-400">{error}</p>
      </Card>
    );
  }

  if (!status) {
    return (
      <Card className="p-4">
        <div className="animate-pulse">
          <div className="h-4 bg-slate-700 rounded w-3/4 mb-2"></div>
          <div className="h-4 bg-slate-700 rounded w-1/2"></div>
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
  
  const progress = status.progress_percentage;

  return (
    <Card className="p-6">
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-white">Evaluation in Progress...</h3>
          <span className="text-sm text-slate-400">{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-2">
          <div
            className="bg-cyan-500 h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <div className="space-y-3">
        {allAgents.map((agentType) => {
          const isCompleted = status.completed_agents.includes(agentType);
          const isPending = status.pending_agents.includes(agentType);
          // Only show cost if agent actually ran (is completed or pending)
          const cost = (isCompleted || isPending) ? (TOOL_COSTS[`verify_${agentType}`] || 0) : 0;

          return (
            <div
              key={agentType}
              className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50"
            >
              <div className="flex items-center gap-3">
                <span className="text-xl">{AGENT_ICONS[agentType] || '🤖'}</span>
                <div>
                  <p className="text-sm font-medium text-white">
                    {AGENT_LABELS[agentType] || agentType}
                  </p>
                  {cost > 0 && (
                    <p className="text-xs text-slate-400">${cost.toFixed(2)} USDC</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {isCompleted ? (
                  <>
                    <span className="text-green-400">✓</span>
                    <span className="text-xs text-green-400">Completed</span>
                  </>
                ) : isPending ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-cyan-400 border-t-transparent"></div>
                    <span className="text-xs text-cyan-400">In Progress...</span>
                  </>
                ) : (
                  <>
                    <span className="text-slate-500">⏸️</span>
                    <span className="text-xs text-slate-500">Pending</span>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {totalCost > 0 && (
        <div className="mt-4 pt-4 border-t border-slate-700">
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-400">Total Cost So Far</span>
            <span className="text-sm font-medium text-cyan-400">
              ${totalCost.toFixed(2)} USDC
            </span>
          </div>
        </div>
      )}

      {/* Agent Activity Logs - Always show section, even if empty */}
      <div className="mt-4 pt-4 border-t border-slate-700">
          <button
            onClick={() => setShowLogs(!showLogs)}
            className="flex items-center justify-between w-full mb-2 text-left"
          >
            <h4 className="text-sm font-medium text-white">
              Agent Activity Logs ({logs.length})
            </h4>
            <svg
              className={`w-4 h-4 text-slate-400 transition-transform ${showLogs ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {showLogs && (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {logs.length === 0 ? (
                <div className="p-3 rounded bg-slate-800/30 border border-slate-700/50 text-xs text-slate-400 text-center">
                  No activity logs yet. Logs will appear as agents process the claim...
                </div>
              ) : (
                logs.map((log) => {
                const logLevelColors: Record<string, string> = {
                  INFO: 'text-cyan-400',
                  DEBUG: 'text-slate-400',
                  WARNING: 'text-yellow-400',
                  ERROR: 'text-red-400',
                };
                
                const agentIcon = AGENT_ICONS[log.agent_type] || '🤖';
                const time = new Date(log.created_at).toLocaleTimeString();
                
                return (
                  <div
                    key={log.id}
                    className="p-2 rounded bg-slate-800/30 border border-slate-700/50 text-xs"
                  >
                    <div className="flex items-start gap-2">
                      <span className="text-sm">{agentIcon}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-slate-300">
                            {AGENT_LABELS[log.agent_type] || log.agent_type}
                          </span>
                          <span className={`text-xs ${logLevelColors[log.log_level] || 'text-slate-400'}`}>
                            {log.log_level}
                          </span>
                          <span className="text-slate-500 text-[10px]">{time}</span>
                        </div>
                        <p className="text-slate-300 text-xs leading-relaxed">{log.message}</p>
                        {log.metadata && Object.keys(log.metadata).length > 0 && (
                          <details className="mt-1">
                            <summary className="text-slate-500 cursor-pointer text-[10px] hover:text-slate-400">
                              View details
                            </summary>
                            <pre className="mt-1 p-2 rounded bg-slate-900/50 text-[10px] text-slate-400 overflow-x-auto">
                              {JSON.stringify(log.metadata, null, 2)}
                            </pre>
                          </details>
                        )}
                      </div>
                    </div>
                  </div>
                );
              }))}
            </div>
          )}
        </div>

      <div className="mt-4 text-center">
        <p className="text-xs text-slate-500">Auto-refreshing every 2s...</p>
      </div>
    </Card>
  );
}
