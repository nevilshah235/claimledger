// ClaimLedger Frontend Types

export type ClaimStatus = 
  | 'SUBMITTED' 
  | 'EVALUATING' 
  | 'APPROVED' 
  | 'SETTLED' 
  | 'REJECTED' 
  | 'NEEDS_REVIEW';

export type Decision = 'APPROVED' | 'NEEDS_REVIEW' | 'REJECTED';

export interface Claim {
  id: string;
  claimant_address: string;
  claim_amount: number;
  status: ClaimStatus;
  decision: Decision | null;
  confidence: number | null;
  approved_amount: number | null;
  processing_costs: number | null;
  tx_hash: string | null;
  created_at: string;
}

export interface ClaimCreateResponse {
  claim_id: string;
  status: ClaimStatus;
}

export interface EvaluationResult {
  claim_id: string;
  decision: Decision;
  confidence: number;
  approved_amount: number | null;
  reasoning: string;
  processing_costs: number;
}

export interface SettlementResult {
  claim_id: string;
  tx_hash: string;
  amount: number;
  recipient: string;
  status: 'SETTLED';
}

export interface VerificationStep {
  type: 'document' | 'image' | 'fraud';
  label: string;
  price: number;
  completed: boolean;
}

export interface ApiError {
  detail: string;
}

// x402 Payment Response
export interface PaymentRequiredResponse {
  error: string;
  amount: string;
  currency: string;
  gateway_payment_id: string;
  payment_url: string;
  description: string;
}

// Health check
export interface HealthResponse {
  status: 'healthy' | 'unhealthy';
}

// API Info
export interface ApiInfo {
  service: string;
  version: string;
  status: string;
  docs: string;
  endpoints: Record<string, string>;
}

// Authentication Types
export interface RegisterRequest {
  email: string;
  password: string;
  role: 'claimant' | 'insurer';
}

export interface RegisterResponse {
  user_id: string;
  email: string;
  role: string;
  wallet_address: string;
  access_token: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  user_id: string;
  email: string;
  role: string;
  wallet_address: string | null;
  access_token: string;
}

export interface UserInfo {
  user_id: string;
  email: string;
  role: string;
  wallet_address: string | null;
}

export interface WalletInfo {
  wallet_address: string;
  circle_wallet_id: string;
  wallet_set_id: string | null;
  blockchain: string | null;
  balance: any | null;
}
