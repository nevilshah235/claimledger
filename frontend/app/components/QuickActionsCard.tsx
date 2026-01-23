'use client';

import Link from 'next/link';
import { Card } from './ui';

export function QuickActionsCard({
}: {
}) {
  return (
    <Card padding="md" className="w-full card-enhanced">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-sm font-semibold text-text-primary">Quick actions</div>
          <div className="text-xs text-text-secondary">Common tasks in one place.</div>
        </div>
      </div>

      <div className="space-y-3">
        <Link
          href="/login?role=claimant"
          className="flex items-center justify-between rounded-xl border border-border bg-surface px-4 py-3 hover:bg-surface-light hover:border-primary transition-colors"
        >
          <div>
            <div className="text-sm font-semibold text-text-primary">Track a claim</div>
            <div className="text-xs text-text-secondary">Requires login.</div>
          </div>
          <svg className="w-5 h-5 text-text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
        </Link>
      </div>
    </Card>
  );
}

export default QuickActionsCard;
