'use client';

import { HTMLAttributes, forwardRef } from 'react';
import { ClaimStatus } from '@/lib/types';

type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  status?: ClaimStatus;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'badge-submitted',
  success: 'badge-approved',
  warning: 'badge-needs-review',
  error: 'badge-rejected',
  info: 'badge-evaluating',
};

const statusToVariant: Record<ClaimStatus, BadgeVariant> = {
  SUBMITTED: 'default',
  EVALUATING: 'info',
  APPROVED: 'success',
  SETTLED: 'success',
  REJECTED: 'error',
  NEEDS_REVIEW: 'warning',
};

const statusLabels: Record<ClaimStatus, string> = {
  SUBMITTED: 'Submitted',
  EVALUATING: 'Evaluating...',
  APPROVED: 'Approved',
  SETTLED: 'Settled',
  REJECTED: 'Rejected',
  NEEDS_REVIEW: 'Needs Review',
};

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ children, variant, status, className = '', ...props }, ref) => {
    // If status is provided, use it to determine variant
    const resolvedVariant = status ? statusToVariant[status] : (variant || 'default');
    const label = status ? statusLabels[status] : children;
    
    // Special styling for settled status
    const settledStyle = status === 'SETTLED' ? 'badge-settled' : variantStyles[resolvedVariant];
    
    return (
      <span
        ref={ref}
        className={`
          ${settledStyle}
          inline-flex items-center gap-1
          ${className}
        `}
        {...props}
      >
        {status === 'SETTLED' && (
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        )}
        {status === 'EVALUATING' && (
          <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        )}
        {label}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

export default Badge;
