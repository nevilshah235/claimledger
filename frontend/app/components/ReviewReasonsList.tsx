'use client';

import { Card } from './ui';

interface ReviewReasonsListProps {
  reasoning?: string | null;
  reviewReasons?: string[] | null;
  contradictions?: string[] | null;
  humanReviewRequired?: boolean;
}

export function ReviewReasonsList({ 
  reasoning,
  reviewReasons, 
  contradictions,
  humanReviewRequired 
}: ReviewReasonsListProps) {
  const hasReasoning = reasoning && reasoning.trim().length > 0;
  const hasReviewReasons = reviewReasons && reviewReasons.length > 0;
  const hasContradictions = contradictions && contradictions.length > 0;

  // Show if there is AI reasoning, review reasons, and/or contradictions
  if (!hasReasoning && !hasReviewReasons && !hasContradictions) {
    return null;
  }

  return (
    <Card className="p-4 border-amber-500/30 bg-amber-500/10">
      <div className="flex items-start gap-3 mb-3">
        <svg className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <div>
          <p className="text-sm font-medium text-amber-400 mb-1">
            Review Reasons
          </p>
          {humanReviewRequired && (
            <span className="inline-block px-2 py-1 text-xs font-medium bg-amber-500/20 text-amber-300 rounded mb-2">
              Human Review Required
            </span>
          )}
        </div>
      </div>

      {hasReasoning && (
        <div className="mb-4 ml-8">
          <p className="text-xs font-medium text-amber-400/90 mb-1.5 uppercase tracking-wide">AI Reasoning</p>
          <p className="text-sm text-amber-100/95 whitespace-pre-wrap">{reasoning!.trim()}</p>
        </div>
      )}
      
      {hasReviewReasons && (
        <ul className="space-y-2 ml-8 pl-5 list-disc marker:text-amber-400">
          {reviewReasons!.map((reason, index) => (
            <li key={index} className="text-sm text-amber-100">
              {reason}
            </li>
          ))}
        </ul>
      )}

      {hasContradictions && (
        <div className={hasReviewReasons ? 'mt-4' : ''}>
          <p className="text-xs font-medium text-amber-400/90 mb-2 uppercase tracking-wide">Contradictions</p>
          <ul className="space-y-2 ml-8 pl-5 list-disc marker:text-amber-400">
            {contradictions!.map((c, index) => (
              <li key={index} className="text-sm text-amber-100">
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
