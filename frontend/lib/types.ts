// ClaimLedger Frontend Types

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
  | 'REJECTED' 
  | 'APPROVED'; // Legacy support

export interface Claim {
  id: string;
  claimant_address: string;
  claim_amount: number;
  description?: string | null;
  status: ClaimStatus;
  decision: Decision | null;
  confidence: number | null;
  approved_amount: number | null;
  processing_costs: number | null;
  tx_hash: string | null;
  auto_settled?: boolean | null;
  created_at: string;
  requested_data?: string[] | null;
  human_review_required?: boolean;
  decision_overridden?: boolean;
  review_reasons?: string[] | null;
  contradictions?: string[] | null;
}

export interface AutoSettleWalletResponse {
  configured: boolean;
  address?: string | null;
  usdc_balance?: number | null;
  eurc_balance?: number | null;
  gas_balance_arc?: number | null;
  message?: string | null;
}

export interface ClaimCreateResponse {
  claim_id: string;
  status: ClaimStatus;
}

export interface ToolCall {
  tool_name: string; // verify_document, verify_image, verify_fraud, approve_claim
  status: 'pending' | 'completed' | 'failed';
  cost: number | null; // USDC amount
  timestamp: string | null;
}

/** agent_type: document/image/fraud (canonical or verify_* tool names), reasoning, or Phase 2 tools */
export type AgentType =
  | 'document'
  | 'image'
  | 'fraud'
  | 'reasoning'
  | 'verify_document'
  | 'verify_image'
  | 'verify_fraud'
  | 'cross_check_amounts'
  | 'validate_claim_data'
  | 'estimate_repair_cost';

export interface AgentResult {
  agent_type: AgentType;
  result: Record<string, any>;
  confidence: number | null;
  created_at: string;
}

export interface AgentResultsResponse {
  claim_id: string;
  agent_results: AgentResult[];
}

export interface AgentLog {
  id: string;
  claim_id: string;
  agent_type: string;
  message: string;
  log_level: 'INFO' | 'DEBUG' | 'WARNING' | 'ERROR';
  metadata?: Record<string, any> | null;
  created_at: string;
}

export interface AgentLogsResponse {
  claim_id: string;
  logs: AgentLog[];
}

export interface EvaluationStatus {
  claim_id: string;
  status: ClaimStatus;
  completed_agents: string[];
  pending_agents: string[];
  progress_percentage: number;
}

export interface EvaluationResult {
  claim_id: string;
  decision: Decision;
  confidence: number;
  approved_amount: number | null;
  reasoning: string;
  processing_costs: number;
  summary?: string | null;
  auto_approved?: boolean;
  auto_settled?: boolean;
  tx_hash?: string | null;
  review_reasons?: string[] | null;
  contradictions?: string[] | null;
  requested_data?: string[] | null;
  human_review_required?: boolean;
  agent_results?: Record<string, any>;
  tool_calls?: ToolCall[];
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

// Bill Analysis Types
export interface BillLineItem {
  item: string;
  quantity: number;
  unit_price: number;
  total: number;
  market_price?: number | null;  // From web search
  valid: boolean;  // Part exists and is valid
  relevant: boolean;  // Relevant for this claim type
  price_valid: boolean;  // Price is within market range
  validation_notes?: string;  // Why item is valid/invalid
}

export interface BillAnalysis {
  extracted_total: number;
  recommended_amount: number;  // Based on market prices and validation
  line_items: BillLineItem[];
  claim_amount_match: boolean;
  document_amount_match: boolean;
  mismatches: string[];
  validation_summary?: {
    valid_items_count: number;
    invalid_items_count: number;
    overpriced_items_count: number;
    irrelevant_items_count: number;
    total_market_value: number;
  };
}
