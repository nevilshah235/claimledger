/**
 * TypeScript type definitions for ClaimLedger
 */

export type ClaimStatus = 
  | 'SUBMITTED'
  | 'EVALUATING'
  | 'APPROVED'
  | 'SETTLED'
  | 'REJECTED'
  | 'NEEDS_REVIEW'
  | 'AWAITING_DATA';

export type Decision = 
  | 'AUTO_APPROVED'
  | 'APPROVED_WITH_REVIEW'
  | 'NEEDS_REVIEW'
  | 'NEEDS_MORE_DATA'
  | 'INSUFFICIENT_DATA'
  | 'FRAUD_DETECTED'
  | 'REJECTED';

export interface Claim {
  id: string;
  claimant_address: string;
  claim_amount: number;
  status: ClaimStatus;
  decision?: Decision;
  confidence?: number;
  approved_amount?: number;
  processing_costs?: number;
  tx_hash?: string;
  requested_data?: string[];
  human_review_required?: boolean;
  created_at: string;
  updated_at?: string;
}

export interface VerificationStep {
  type: 'document' | 'image' | 'fraud' | 'video' | 'audio';
  label: string;
  price: number;
  completed: boolean;
}

export interface EvaluationResult {
  claim_id: string;
  decision: Decision;
  confidence: number;
  approved_amount?: number;
  reasoning: string;
  processing_costs: number;
  summary?: string;
  auto_approved: boolean;
  auto_settled: boolean;
  tx_hash?: string;
  review_reasons?: string[];
  requested_data?: string[];
  human_review_required?: boolean;
  agent_results?: any;
  tool_calls?: ToolCall[];
}

export interface ToolCall {
  tool_name: string;
  status: string;
  cost?: number;
  timestamp?: string;
}

export interface AgentResult {
  agent_type: string;
  result: any;
  confidence?: number;
  created_at: string;
}

export interface AgentLog {
  id: string;
  claim_id: string;
  agent_type: string;
  message: string;
  log_level: string;
  metadata?: any;
  created_at: string;
}

export interface EvaluationStatus {
  claim_id: string;
  status: string;
  completed_agents: string[];
  pending_agents: string[];
  progress_percentage: number;
}

export interface WalletInfo {
  wallet_address: string;
  circle_wallet_id?: string;
  wallet_set_id?: string;
  blockchain?: string;
  balance?: {
    balances?: Array<{
      amount: string;
      currency: string;
    }>;
  };
}

export interface BillAnalysis {
  items: Array<{
    description: string;
    amount: number;
    category?: string;
  }>;
  total: number;
  currency: string;
}
