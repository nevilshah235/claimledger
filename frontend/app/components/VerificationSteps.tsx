'use client';

import { VerificationStep } from '@/lib/types';

interface VerificationStepsProps {
  steps?: VerificationStep[];
  totalCost?: number;
}

const defaultSteps: VerificationStep[] = [
  { type: 'document', label: 'Document', price: 0.10, completed: false },
  { type: 'image', label: 'Image', price: 0.15, completed: false },
  { type: 'fraud', label: 'Fraud', price: 0.10, completed: false },
];

export function VerificationSteps({ 
  steps = defaultSteps, 
  totalCost = 0.35 
}: VerificationStepsProps) {
  const completedSteps = steps.filter(s => s.completed).length;
  const allCompleted = completedSteps === steps.length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-slate-300">Verification Steps</h4>
        <span className="text-xs text-slate-400">
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
              
              {/* Label & Price */}
              <span className={step.completed ? 'text-emerald-400' : 'text-slate-400'}>
                {step.label}
              </span>
              <span className={`text-xs ${step.completed ? 'text-emerald-400/70' : 'text-slate-500'}`}>
                ${step.price.toFixed(2)}
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

      {/* Total Cost */}
      {allCompleted && totalCost > 0 && (
        <div className="flex items-center justify-between pt-3 border-t border-white/10">
          <div>
            <span className="text-sm text-slate-400">Total Processing Cost</span>
            <p className="text-xs text-slate-500 mt-0.5">Charged for AI verification services</p>
          </div>
          <span className="text-sm font-semibold text-cyan-400">${totalCost.toFixed(2)} USDC</span>
        </div>
      )}
      {allCompleted && totalCost === 0 && (
        <div className="pt-3 border-t border-white/10">
          <p className="text-xs text-slate-500 italic">
            Processing costs will be calculated after evaluation completes.
          </p>
        </div>
      )}
    </div>
  );
}

export default VerificationSteps;
