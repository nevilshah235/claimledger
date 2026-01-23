'use client';

import { VerificationStep } from '@/lib/types';

interface VerificationStepsProps {
  steps?: VerificationStep[];
  totalCost?: number;
}

const defaultSteps: VerificationStep[] = [
  { type: 'document', label: 'Document', price: 0, completed: false },
  { type: 'image', label: 'Image', price: 0, completed: false },
  { type: 'fraud', label: 'Fraud', price: 0, completed: false },
];

export function VerificationSteps({ 
  steps = defaultSteps, 
  totalCost = 0 
}: VerificationStepsProps) {
  const completedSteps = steps.filter(s => s.completed).length;
  const allCompleted = completedSteps === steps.length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-slate-200">Verification Steps</h4>
        <span className="text-xs text-slate-300">
          {completedSteps}/{steps.length} complete
        </span>
      </div>

      {/* Steps */}
      <div className="flex items-center gap-2">
        {steps.map((step, index) => (
          <div key={step.type} className="flex items-center">
            {/* Step */}
            <div
              className={`
                verification-step
                ${step.completed ? 'completed' : 'pending'}
              `}
            >
              {/* Icon */}
              {step.completed ? (
                <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
              
              {/* Label (price hidden: evaluations are free) */}
              <span className={step.completed ? 'text-emerald-400' : 'text-slate-400'}>
                {step.label}
              </span>
            </div>

            {/* Connector */}
            {index < steps.length - 1 && (
              <div className={`w-4 h-0.5 mx-1 ${
                step.completed ? 'bg-emerald-400/50' : 'bg-slate-600'
              }`} />
            )}
          </div>
        ))}
      </div>

      {/* Evaluations are free – no cost block shown */}
      {allCompleted && (
        <div className="pt-3 border-t border-white/10">
          <p className="text-xs text-slate-300 italic">
            Evaluations are included at no cost.
          </p>
        </div>
      )}
    </div>
  );
}

export default VerificationSteps;
