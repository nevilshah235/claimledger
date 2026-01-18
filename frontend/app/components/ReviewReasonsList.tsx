'use client';

import { Card } from './ui';

interface ReviewReasonsListProps {
  reviewReasons?: string[] | null;
  humanReviewRequired?: boolean;
}

export function ReviewReasonsList({ 
  reviewReasons, 
  humanReviewRequired 
}: ReviewReasonsListProps) {
  if (!reviewReasons || reviewReasons.length === 0) {
    if (!humanReviewRequired) {
      return null;
    }
    // Show generic message if human review required but no specific reasons
    return (
      <Card className="p-4 border-orange-500/30 bg-orange-500/10">
        <div className="flex items-start gap-3">
          <span className="text-orange-400 text-xl">⚠️</span>
          <div>
            <p className="text-sm font-medium text-orange-400 mb-1">
              Human Review Required
            </p>
            <p className="text-sm text-slate-300">
              This claim requires manual review by an insurer.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-4 border-orange-500/30 bg-orange-500/10">
      <div className="flex items-start gap-3 mb-3">
        <span className="text-orange-400 text-xl">⚠️</span>
        <div>
          <p className="text-sm font-medium text-orange-400 mb-1">
            Review Reasons
          </p>
          {humanReviewRequired && (
            <span className="inline-block px-2 py-1 text-xs font-medium bg-orange-500/20 text-orange-300 rounded mb-2">
              Human Review Required
            </span>
          )}
        </div>
      </div>
      
      <ul className="space-y-2 ml-8">
        {reviewReasons.map((reason, index) => (
          <li key={index} className="text-sm text-slate-300 flex items-start gap-2">
            <span className="text-orange-400 mt-1">•</span>
            <span>{reason}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
