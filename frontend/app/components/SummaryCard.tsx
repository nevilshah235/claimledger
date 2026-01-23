'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card } from './ui';
import { Decision } from '@/lib/types';

interface SummaryCardProps {
  confidence: number | null;
  decision: Decision | null;
  summary?: string | null;
  approvedAmount?: number | null;
  processingCosts?: number | null;
  humanReviewRequired?: boolean;
}

const DECISION_COLORS: Record<string, string> = {
  AUTO_APPROVED: 'bg-green-500/20 border-green-500/50 text-green-400',
  APPROVED_WITH_REVIEW: 'bg-yellow-500/20 border-yellow-500/50 text-yellow-400',
  NEEDS_REVIEW: 'bg-orange-500/20 border-orange-500/50 text-orange-400',
  NEEDS_MORE_DATA: 'bg-blue-500/20 border-blue-500/50 text-blue-400',
  INSUFFICIENT_DATA: 'bg-red-500/20 border-red-500/50 text-red-400',
  REJECTED: 'bg-red-500/20 border-red-500/50 text-red-400',
  APPROVED: 'bg-green-500/20 border-green-500/50 text-green-400', // Legacy
};

const DECISION_LABELS: Record<string, string> = {
  AUTO_APPROVED: 'Auto-Approved',
  APPROVED_WITH_REVIEW: 'Approved with Review',
  NEEDS_REVIEW: 'Needs Review',
  NEEDS_MORE_DATA: 'Needs More Data',
  INSUFFICIENT_DATA: 'Insufficient Data',
  REJECTED: 'Rejected',
  APPROVED: 'Approved', // Legacy
};

const CONFIDENCE_THRESHOLDS = [
  { threshold: 0.95, label: 'Auto-approved', color: 'text-green-400' },
  { threshold: 0.85, label: 'Approved with review', color: 'text-yellow-400' },
  { threshold: 0.70, label: 'Needs review', color: 'text-orange-400' },
  { threshold: 0.50, label: 'Needs more data', color: 'text-blue-400' },
  { threshold: 0.00, label: 'Insufficient data', color: 'text-red-400' },
];

function getConfidenceThreshold(confidence: number): string {
  for (const { threshold, label } of CONFIDENCE_THRESHOLDS) {
    if (confidence >= threshold) {
      return label;
    }
  }
  return 'Insufficient data';
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.95) return 'text-green-400';
  if (confidence >= 0.85) return 'text-yellow-400';
  if (confidence >= 0.70) return 'text-orange-400';
  if (confidence >= 0.50) return 'text-blue-400';
  return 'text-red-400';
}

export function SummaryCard({
  confidence,
  decision,
  summary,
  approvedAmount,
  processingCosts,
  humanReviewRequired,
}: SummaryCardProps) {
  const confidencePercent = confidence ? Math.round(confidence * 100) : 0;
  const decisionKey = decision || 'NEEDS_REVIEW';
  const decisionColor = DECISION_COLORS[decisionKey] || DECISION_COLORS.NEEDS_REVIEW;
  const decisionLabel = DECISION_LABELS[decisionKey] || 'Unknown';

  return (
    <Card className="p-6 admin-card">
      {/* Confidence Score */}
      {confidence !== null && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm admin-text-secondary">AI Confidence</span>
            <div className="flex items-center gap-2">
              <span className={`text-2xl font-bold ${getConfidenceColor(confidence)}`}>
                {confidencePercent}%
              </span>
              <div
                className="group relative cursor-help"
                title={`Confidence threshold: ${getConfidenceThreshold(confidence)}`}
              >
                <svg
                  className="w-4 h-4 admin-text-secondary"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
            </div>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-3">
            <div
              className={`h-3 rounded-full transition-all duration-300 ${
                confidence >= 0.95
                  ? 'bg-green-500'
                  : confidence >= 0.85
                  ? 'bg-yellow-500'
                  : confidence >= 0.70
                  ? 'bg-orange-500'
                  : confidence >= 0.50
                  ? 'bg-blue-500'
                  : 'bg-red-500'
              }`}
              style={{ width: `${confidencePercent}%` }}
            />
          </div>
          <p className="text-xs admin-text-secondary mt-1">
            {getConfidenceThreshold(confidence)}
          </p>
        </div>
      )}

      {/* Decision Badge */}
      {decision && (
        <div className="mb-4">
          <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border ${decisionColor}`}>
            <span className="text-sm font-medium">{decisionLabel}</span>
            {humanReviewRequired && (
              <span className="text-xs px-2 py-0.5 bg-yellow-500/20 text-yellow-300 rounded">
                Human Review Required
              </span>
            )}
          </div>
        </div>
      )}

      {/* Summary Text */}
      {summary && (
        <div className="mb-4 prose prose-invert prose-sm max-w-none">
          <div className="text-sm admin-text-primary leading-relaxed markdown-content">
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
              {summary}
            </ReactMarkdown>
          </div>
        </div>
      )}

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-4 pt-4 border-t border-white/10">
        {approvedAmount !== null && approvedAmount !== undefined && (
          <div>
            <p className="text-xs admin-text-secondary mb-1">Approved Amount</p>
            <p className="text-lg font-bold text-emerald-400">
              ${approvedAmount.toFixed(2)} USDC
            </p>
          </div>
        )}
        {processingCosts !== null && processingCosts !== undefined && (
          <div>
            <p className="text-xs admin-text-secondary mb-1">Processing Cost</p>
            <p className="text-lg font-bold text-cyan-400">
              ${processingCosts.toFixed(2)} USDC
            </p>
          </div>
        )}
      </div>
    </Card>
  );
}
