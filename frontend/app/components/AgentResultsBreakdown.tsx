'use client';

import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card } from './ui';
import { AgentResult, ToolCall, BillAnalysis } from '@/lib/types';
import { api } from '@/lib/api';

interface AgentResultsBreakdownProps {
  claimId: string;
  toolCalls?: ToolCall[];
}

const AGENT_LABELS: Record<string, string> = {
  document: 'Document Agent',
  image: 'Image Agent',
  fraud: 'Fraud Agent',
  reasoning: 'Reasoning Agent',
};

const AGENT_ICONS: Record<string, string> = {
  document: '📄',
  image: '🖼️',
  fraud: '🛡️',
  reasoning: '🧠',
};

const AGENT_COLORS: Record<string, string> = {
  document: 'border-blue-500/50 bg-blue-500/10',
  image: 'border-purple-500/50 bg-purple-500/10',
  fraud: 'border-red-500/50 bg-red-500/10',
  reasoning: 'border-green-500/50 bg-green-500/10',
};

const TOOL_LABELS: Record<string, string> = {
  verify_document: 'Verify Document',
  verify_image: 'Verify Image',
  verify_fraud: 'Verify Fraud',
  approve_claim: 'Approve Claim',
};

function formatToolCall(toolCall: ToolCall): string {
  const label = TOOL_LABELS[toolCall.tool_name] || toolCall.tool_name;
  if (toolCall.cost !== null && toolCall.cost !== undefined) {
    return `${label} - $${toolCall.cost.toFixed(2)} USDC`;
  }
  return label;
}

export function AgentResultsBreakdown({ claimId, toolCalls }: AgentResultsBreakdownProps) {
  const [agentResults, setAgentResults] = useState<AgentResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedAgents, setExpandedAgents] = useState<Set<string>>(new Set());

  useEffect(() => {
    const fetchResults = async () => {
      try {
        setLoading(true);
        setError(null); // Clear previous errors
        const response = await api.agent.getResults(claimId);
        setAgentResults(response.agent_results || []);
      } catch (err) {
        // Check if it's a 404 (not found) - this is expected if evaluation hasn't completed
        const errorMessage = err instanceof Error ? err.message : 'Failed to fetch agent results';
        const isNotFound = errorMessage.toLowerCase().includes('not found') || 
                          errorMessage.toLowerCase().includes('404') ||
                          errorMessage.toLowerCase().includes('claim not found');
        
        if (isNotFound) {
          // Don't treat 404 as an error - just show empty state
          setAgentResults([]);
          setError(null);
        } else {
          setError(errorMessage);
        }
      } finally {
        setLoading(false);
      }
    };

    if (claimId) {
      fetchResults();
    }
  }, [claimId]);

  const toggleExpand = (agentType: string) => {
    const newExpanded = new Set(expandedAgents);
    if (newExpanded.has(agentType)) {
      newExpanded.delete(agentType);
    } else {
      newExpanded.add(agentType);
    }
    setExpandedAgents(newExpanded);
  };

  if (loading) {
    return (
      <Card className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-slate-700 rounded w-1/4"></div>
          <div className="h-20 bg-slate-700 rounded"></div>
          <div className="h-20 bg-slate-700 rounded"></div>
        </div>
      </Card>
    );
  }

  if (error) {
    // Check if it's a 404 (not found) vs other error
    const isNotFound = error.toLowerCase().includes('not found') || error.toLowerCase().includes('404');
    
    return (
      <Card className="p-6">
        <div className="text-center py-8">
          <div className="w-16 h-16 rounded-full bg-slate-800/50 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <p className="text-sm text-slate-400 mb-2">
            {isNotFound 
              ? 'Agent results not available yet' 
              : 'Failed to load agent results'}
          </p>
          {!isNotFound && (
            <p className="text-xs text-slate-500">{error}</p>
          )}
          <p className="text-xs text-slate-500 mt-2">
            {isNotFound 
              ? 'Results will appear after the claim has been evaluated.' 
              : 'Please try refreshing the page.'}
          </p>
        </div>
      </Card>
    );
  }

  if (agentResults.length === 0) {
    return (
      <Card className="p-6">
        <div className="text-center py-8">
          <div className="w-16 h-16 rounded-full bg-slate-800/50 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <p className="text-sm text-slate-400 mb-2">No agent results available yet.</p>
          <p className="text-xs text-slate-500">
            Results will appear after the claim has been evaluated.
          </p>
        </div>
      </Card>
    );
  }

  // Get tool calls for each agent type
  const getToolCallsForAgent = (agentType: string): ToolCall[] => {
    if (!toolCalls) return [];
    
    if (agentType === 'document') {
      return toolCalls.filter(tc => tc.tool_name === 'verify_document');
    } else if (agentType === 'image') {
      return toolCalls.filter(tc => tc.tool_name === 'verify_image');
    } else if (agentType === 'fraud') {
      return toolCalls.filter(tc => tc.tool_name === 'verify_fraud');
    } else if (agentType === 'reasoning') {
      // Reasoning agent doesn't call tools directly, but approve_claim might be related
      return toolCalls.filter(tc => tc.tool_name === 'approve_claim');
    }
    return [];
  };

  return (
    <div className="space-y-4">
      {agentResults.map((agentResult) => {
        const isExpanded = expandedAgents.has(agentResult.agent_type);
        const agentToolCalls = getToolCallsForAgent(agentResult.agent_type);
        const confidencePercent = agentResult.confidence
          ? Math.round(agentResult.confidence * 100)
          : 0;

        return (
          <Card
            key={agentResult.agent_type}
            className={`p-4 border ${AGENT_COLORS[agentResult.agent_type] || 'border-slate-700'}`}
          >
            {/* Header */}
            <div
              className="flex items-center justify-between cursor-pointer"
              onClick={() => toggleExpand(agentResult.agent_type)}
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">
                  {AGENT_ICONS[agentResult.agent_type] || '🤖'}
                </span>
                <div>
                  <h3 className="text-sm font-medium text-white">
                    {AGENT_LABELS[agentResult.agent_type] || agentResult.agent_type}
                  </h3>
                  {agentResult.confidence !== null && (
                    <div className="flex items-center gap-2 mt-1">
                      <div className="w-24 bg-slate-700 rounded-full h-1.5">
                        <div
                          className={`h-1.5 rounded-full ${
                            agentResult.confidence >= 0.70 ? 'bg-green-500' : agentResult.confidence >= 0.40 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${confidencePercent}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-400">{confidencePercent}%</span>
                    </div>
                  )}
                </div>
              </div>
              <button className="text-slate-400 hover:text-white transition-colors">
                {isExpanded ? (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                )}
              </button>
            </div>

            {/* Expanded Content */}
            {isExpanded && (
              <div className="mt-4 pt-4 border-t border-slate-700 space-y-4">
                {/* Tool Calls */}
                {agentToolCalls.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-slate-400 mb-2">Tool Calls:</p>
                    <div className="space-y-1">
                      {agentToolCalls.map((toolCall, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between text-xs p-2 rounded bg-slate-800/50"
                        >
                          <div className="flex items-center gap-2">
                            {toolCall.status === 'completed' && (
                              <span className="text-green-400">✓</span>
                            )}
                            {toolCall.status === 'pending' && (
                              <span className="text-yellow-400">⏳</span>
                            )}
                            {toolCall.status === 'failed' && (
                              <span className="text-red-400">✗</span>
                            )}
                            <span className="text-slate-300">
                              {formatToolCall(toolCall)}
                            </span>
                          </div>
                          <span
                            className={`text-xs ${
                              toolCall.status === 'completed'
                                ? 'text-green-400'
                                : toolCall.status === 'pending'
                                ? 'text-yellow-400'
                                : 'text-red-400'
                            }`}
                          >
                            {toolCall.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Summary */}
                {agentResult.result.summary && (
                  <div>
                    <p className="text-xs font-medium text-slate-400 mb-1">Summary:</p>
                    <div className="text-sm text-slate-300 markdown-content">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                          ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                          ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                          li: ({ children }) => <li className="ml-2">{children}</li>,
                          strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                          em: ({ children }) => <em className="italic">{children}</em>,
                          code: ({ children, className }) => {
                            const isInline = !className;
                            return isInline ? (
                              <code className="px-1.5 py-0.5 bg-slate-800 rounded text-cyan-400 text-xs font-mono">{children}</code>
                            ) : (
                              <code className="block p-3 bg-slate-900 rounded-lg text-xs font-mono text-slate-300 overflow-x-auto">{children}</code>
                            );
                          },
                          pre: ({ children }) => <pre className="mb-2">{children}</pre>,
                          h1: ({ children }) => <h1 className="text-lg font-bold text-white mb-2 mt-4 first:mt-0">{children}</h1>,
                          h2: ({ children }) => <h2 className="text-base font-bold text-white mb-2 mt-3 first:mt-0">{children}</h2>,
                          h3: ({ children }) => <h3 className="text-sm font-bold text-white mb-1 mt-2 first:mt-0">{children}</h3>,
                          blockquote: ({ children }) => <blockquote className="border-l-4 border-slate-600 pl-4 italic text-slate-400 my-2">{children}</blockquote>,
                          a: ({ href, children }) => <a href={href} className="text-cyan-400 hover:text-cyan-300 underline" target="_blank" rel="noopener noreferrer">{children}</a>,
                        }}
                      >
                        {agentResult.result.summary}
                      </ReactMarkdown>
                    </div>
                  </div>
                )}

                {/* Extracted Data */}
                {agentResult.result.extracted_data && (() => {
                  const extractedData = agentResult.result.extracted_data;
                  
                  // Check if extraction failed
                  if (extractedData.extraction_failed || extractedData.error || 
                      (extractedData.metadata?.extraction_method === 'failed')) {
                    return (
                      <div>
                        <p className="text-xs font-medium text-red-400 mb-2">Extraction Failed</p>
                        <div className="p-3 rounded bg-red-500/10 border border-red-500/30 text-xs">
                          <p className="text-red-400 font-medium mb-1">⚠️ Document extraction failed</p>
                          <p className="text-slate-300">
                            {extractedData.metadata?.notes || 
                             extractedData.error || 
                             'Document extraction failed. Please ensure the API is properly configured.'}
                          </p>
                        </div>
                      </div>
                    );
                  }
                  
                  // Helper to format field names
                  const formatKey = (key: string) => 
                    key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                  
                  // Helper to render a value
                  const renderValue = (value: any, depth = 0): React.ReactNode => {
                    if (value === null || value === undefined) {
                      return <span className="text-slate-500 italic">null</span>;
                    }
                    
                    if (typeof value === 'boolean') {
                      return <span className={value ? 'text-green-400' : 'text-red-400'}>{value ? 'Yes' : 'No'}</span>;
                    }
                    
                    if (typeof value === 'number') {
                      // Format monetary values
                      if (value % 1 !== 0 || value > 100) {
                        return <span className="text-emerald-400 font-medium">${value.toFixed(2)}</span>;
                      }
                      return <span className="text-slate-300">{value}</span>;
                    }
                    
                    if (Array.isArray(value)) {
                      if (value.length === 0) {
                        return <span className="text-slate-500 italic">Empty array</span>;
                      }
                      return (
                        <div className="ml-4 space-y-1">
                          {value.map((item, idx) => (
                            <div key={idx} className="border-l-2 border-slate-600 pl-2">
                              {typeof item === 'object' && item !== null ? (
                                <div className="space-y-1">
                                  {Object.entries(item).map(([k, v]) => (
                                    <div key={k} className="text-xs">
                                      <span className="text-slate-400">{formatKey(k)}: </span>
                                      {renderValue(v, depth + 1)}
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <span className="text-slate-300">{String(item)}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      );
                    }
                    
                    if (typeof value === 'object') {
                      return (
                        <div className="ml-4 space-y-1 border-l-2 border-slate-600 pl-2">
                          {Object.entries(value).map(([k, v]) => (
                            <div key={k} className="text-xs">
                              <span className="text-slate-400">{formatKey(k)}: </span>
                              {renderValue(v, depth + 1)}
                            </div>
                          ))}
                        </div>
                      );
                    }
                    
                    return <span className="text-slate-300">{String(value)}</span>;
                  };
                  
                  // Check if it's the new structure with document_classification
                  const hasNewStructure = extractedData.document_classification || extractedData.extracted_fields;
                  
                  return (
                    <div>
                      <p className="text-xs font-medium text-slate-400 mb-2">Extracted Data:</p>
                      <div className="space-y-2 text-xs">
                        {hasNewStructure ? (
                          <>
                            {/* Document Classification */}
                            {extractedData.document_classification && (
                              <div className="p-2 rounded bg-slate-800/50">
                                <div className="text-slate-300 font-medium mb-1">Document Classification</div>
                                {Object.entries(extractedData.document_classification).map(([key, value]) => (
                                  <div key={key} className="flex items-start gap-2">
                                    <span className="text-slate-400">{formatKey(key)}:</span>
                                    {renderValue(value)}
                                  </div>
                                ))}
                              </div>
                            )}
                            
                            {/* Extracted Fields */}
                            {extractedData.extracted_fields && (
                              <div className="p-2 rounded bg-slate-800/50">
                                <div className="text-slate-300 font-medium mb-1">Extracted Fields</div>
                                <div className="space-y-1">
                                  {Object.entries(extractedData.extracted_fields).map(([key, value]) => (
                                    <div key={key} className="flex items-start gap-2">
                                      <span className="text-slate-400">{formatKey(key)}:</span>
                                      {renderValue(value)}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            
                            {/* Line Items */}
                            {extractedData.line_items && Array.isArray(extractedData.line_items) && extractedData.line_items.length > 0 && (
                              <div className="p-2 rounded bg-slate-800/50">
                                <div className="text-slate-300 font-medium mb-1">Line Items ({extractedData.line_items.length})</div>
                                {renderValue(extractedData.line_items)}
                              </div>
                            )}
                            
                            {/* Tables */}
                            {extractedData.tables && Array.isArray(extractedData.tables) && extractedData.tables.length > 0 && (
                              <div className="p-2 rounded bg-slate-800/50">
                                <div className="text-slate-300 font-medium mb-1">Tables ({extractedData.tables.length})</div>
                                {renderValue(extractedData.tables)}
                              </div>
                            )}
                            
                            {/* Metadata */}
                            {extractedData.metadata && (
                              <div className="p-2 rounded bg-slate-800/50">
                                <div className="text-slate-300 font-medium mb-1">Metadata</div>
                                {Object.entries(extractedData.metadata).map(([key, value]) => (
                                  <div key={key} className="flex items-start gap-2">
                                    <span className="text-slate-400">{formatKey(key)}:</span>
                                    {renderValue(value)}
                                  </div>
                                ))}
                              </div>
                            )}
                            
                            {/* Other top-level fields */}
                            {Object.entries(extractedData)
                              .filter(([key]) => !['document_classification', 'extracted_fields', 'line_items', 'tables', 'metadata'].includes(key))
                              .map(([key, value]) => (
                                <div key={key} className="flex items-start gap-2">
                                  <span className="text-slate-400">• {formatKey(key)}:</span>
                                  {renderValue(value)}
                                </div>
                              ))}
                          </>
                        ) : (
                          // Fallback to old structure - render all fields
                          <div className="space-y-1">
                            {Object.entries(extractedData).map(([key, value]) => (
                              <div key={key} className="flex items-start gap-2">
                                <span className="text-slate-400">• {formatKey(key)}:</span>
                                {renderValue(value)}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })()}

                {/* Additional Result Data */}
                {agentResult.result.damage_assessment && (
                  <div>
                    <p className="text-xs font-medium text-slate-400 mb-2">Damage Assessment:</p>
                    <div className="text-sm text-slate-300">
                      {JSON.stringify(agentResult.result.damage_assessment, null, 2)}
                    </div>
                  </div>
                )}

                {agentResult.result.fraud_score !== undefined && (
                  <div>
                    <p className="text-xs font-medium text-slate-400 mb-1">Fraud Score:</p>
                    <p className="text-sm text-slate-300">
                      {agentResult.result.fraud_score} ({agentResult.result.risk_level || 'N/A'})
                    </p>
                  </div>
                )}

                {/* Bill Analysis */}
                {agentResult.result.bill_analysis && (
                  <div>
                    <p className="text-xs font-medium text-slate-400 mb-2">Bill Analysis:</p>
                    {(() => {
                      const billAnalysis = agentResult.result.bill_analysis as BillAnalysis;
                      return (
                        <div className="space-y-3">
                          {/* Extracted Total and Recommended Amount */}
                          <div className="grid grid-cols-2 gap-3">
                            <div className="p-2 rounded bg-slate-800/50">
                              <p className="text-xs text-slate-400 mb-1">Extracted Total</p>
                              <p className="text-sm font-bold text-slate-300">
                                ${billAnalysis.extracted_total.toFixed(2)}
                              </p>
                            </div>
                            {billAnalysis.recommended_amount !== undefined && 
                             Math.abs(billAnalysis.recommended_amount - billAnalysis.extracted_total) > 0.01 && (
                              <div className="p-2 rounded bg-yellow-500/10 border border-yellow-500/30">
                                <p className="text-xs text-yellow-400 mb-1">Recommended Amount</p>
                                <p className="text-sm font-bold text-yellow-300">
                                  ${billAnalysis.recommended_amount.toFixed(2)}
                                </p>
                                <p className="text-xs text-yellow-400 mt-1">
                                  Based on market validation
                                </p>
                              </div>
                            )}
                          </div>

                          {/* Match Indicators */}
                          <div className="flex items-center gap-4 text-xs">
                            <div className="flex items-center gap-1">
                              {billAnalysis.claim_amount_match ? (
                                <span className="text-green-400">✓</span>
                              ) : (
                                <span className="text-red-400">✗</span>
                              )}
                              <span className="text-slate-400">Claim Amount Match</span>
                            </div>
                            <div className="flex items-center gap-1">
                              {billAnalysis.document_amount_match ? (
                                <span className="text-green-400">✓</span>
                              ) : (
                                <span className="text-red-400">✗</span>
                              )}
                              <span className="text-slate-400">Document Amount Match</span>
                            </div>
                          </div>

                          {/* Mismatches */}
                          {billAnalysis.mismatches && billAnalysis.mismatches.length > 0 && (
                            <div className="p-2 rounded bg-red-500/10 border border-red-500/30">
                              <p className="text-xs font-medium text-red-400 mb-1">Mismatches:</p>
                              <ul className="list-disc list-inside text-xs text-red-300 space-y-1">
                                {billAnalysis.mismatches.map((mismatch, idx) => (
                                  <li key={idx}>{mismatch}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Line Items Table */}
                          {billAnalysis.line_items && billAnalysis.line_items.length > 0 && (
                            <div>
                              <p className="text-xs font-medium text-slate-400 mb-2">Line Items:</p>
                              <div className="overflow-x-auto">
                                <table className="w-full text-xs">
                                  <thead>
                                    <tr className="border-b border-slate-700">
                                      <th className="text-left p-2 text-slate-400">Item</th>
                                      <th className="text-right p-2 text-slate-400">Qty</th>
                                      <th className="text-right p-2 text-slate-400">Unit Price</th>
                                      <th className="text-right p-2 text-slate-400">Total</th>
                                      {billAnalysis.line_items.some(item => item.market_price) && (
                                        <th className="text-right p-2 text-slate-400">Market Price</th>
                                      )}
                                      <th className="text-center p-2 text-slate-400">Status</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {billAnalysis.line_items.map((item, idx) => {
                                      const isOverpriced = item.market_price && 
                                        item.unit_price > item.market_price * 1.2;
                                      const statusIcon = item.valid && item.relevant && item.price_valid ? '✓' :
                                        !item.valid ? '✗' :
                                        !item.relevant ? '⚠️' :
                                        isOverpriced ? '⚠️' : 'ℹ️';
                                      const statusColor = item.valid && item.relevant && item.price_valid ? 'text-green-400' :
                                        !item.valid ? 'text-red-400' :
                                        isOverpriced ? 'text-yellow-400' : 'text-blue-400';
                                      
                                      return (
                                        <tr key={idx} className="border-b border-slate-800">
                                          <td className="p-2 text-slate-300">{item.item}</td>
                                          <td className="p-2 text-right text-slate-300">{item.quantity}</td>
                                          <td className="p-2 text-right text-slate-300">
                                            ${item.unit_price.toFixed(2)}
                                          </td>
                                          <td className="p-2 text-right text-slate-300">
                                            ${item.total.toFixed(2)}
                                          </td>
                                          {billAnalysis.line_items.some(i => i.market_price) && (
                                            <td className="p-2 text-right text-slate-400">
                                              {item.market_price ? `$${item.market_price.toFixed(2)}` : 'N/A'}
                                            </td>
                                          )}
                                          <td className="p-2 text-center">
                                            <span className={statusColor} title={item.validation_notes || ''}>
                                              {statusIcon}
                                            </span>
                                          </td>
                                        </tr>
                                      );
                                    })}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}

                          {/* Validation Summary */}
                          {billAnalysis.validation_summary && (
                            <div className="p-2 rounded bg-slate-800/50">
                              <p className="text-xs font-medium text-slate-400 mb-2">Validation Summary:</p>
                              <div className="grid grid-cols-2 gap-2 text-xs">
                                <div>
                                  <span className="text-slate-400">Valid Items: </span>
                                  <span className="text-green-400 font-medium">
                                    {billAnalysis.validation_summary.valid_items_count}
                                  </span>
                                </div>
                                <div>
                                  <span className="text-slate-400">Invalid Items: </span>
                                  <span className="text-red-400 font-medium">
                                    {billAnalysis.validation_summary.invalid_items_count}
                                  </span>
                                </div>
                                <div>
                                  <span className="text-slate-400">Overpriced Items: </span>
                                  <span className="text-yellow-400 font-medium">
                                    {billAnalysis.validation_summary.overpriced_items_count}
                                  </span>
                                </div>
                                <div>
                                  <span className="text-slate-400">Irrelevant Items: </span>
                                  <span className="text-orange-400 font-medium">
                                    {billAnalysis.validation_summary.irrelevant_items_count}
                                  </span>
                                </div>
                                <div className="col-span-2 pt-1 border-t border-slate-700">
                                  <span className="text-slate-400">Total Market Value: </span>
                                  <span className="text-cyan-400 font-medium">
                                    ${billAnalysis.validation_summary.total_market_value.toFixed(2)}
                                  </span>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                )}

                {/* Notes */}
                {agentResult.result.notes && (
                  <div>
                    <p className="text-xs font-medium text-slate-400 mb-1">Notes:</p>
                    <div className="text-sm text-slate-300 markdown-content">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                          ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                          ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                          li: ({ children }) => <li className="ml-2">{children}</li>,
                          strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                          em: ({ children }) => <em className="italic">{children}</em>,
                          code: ({ children, className }) => {
                            const isInline = !className;
                            return isInline ? (
                              <code className="px-1.5 py-0.5 bg-slate-800 rounded text-cyan-400 text-xs font-mono">{children}</code>
                            ) : (
                              <code className="block p-3 bg-slate-900 rounded-lg text-xs font-mono text-slate-300 overflow-x-auto">{children}</code>
                            );
                          },
                          pre: ({ children }) => <pre className="mb-2">{children}</pre>,
                          h1: ({ children }) => <h1 className="text-lg font-bold text-white mb-2 mt-4 first:mt-0">{children}</h1>,
                          h2: ({ children }) => <h2 className="text-base font-bold text-white mb-2 mt-3 first:mt-0">{children}</h2>,
                          h3: ({ children }) => <h3 className="text-sm font-bold text-white mb-1 mt-2 first:mt-0">{children}</h3>,
                          blockquote: ({ children }) => <blockquote className="border-l-4 border-slate-600 pl-4 italic text-slate-400 my-2">{children}</blockquote>,
                          a: ({ href, children }) => <a href={href} className="text-cyan-400 hover:text-cyan-300 underline" target="_blank" rel="noopener noreferrer">{children}</a>,
                        }}
                      >
                        {agentResult.result.notes}
                      </ReactMarkdown>
                    </div>
                  </div>
                )}

                {/* Timestamp */}
                {agentResult.created_at && (
                  <div className="pt-2 border-t border-slate-700">
                    <p className="text-xs text-slate-500">
                      Completed: {new Date(agentResult.created_at).toLocaleString()}
                    </p>
                  </div>
                )}
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}
