/**
 * API Client for ClaimLedger Backend
 * 
 * Uses NEXT_PUBLIC_API_URL environment variable for API base URL.
 * Defaults to http://localhost:8000 for local development.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Get authentication token from localStorage
 */
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('auth_token');
}

/**
 * Get auth headers for API requests
 */
function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Make API request with error handling
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_URL}${endpoint}`;
  const headers = { ...getAuthHeaders(), ...options.headers };
  
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      detail: response.statusText || 'Request failed',
    }));
    throw new Error(error.detail || error.message || 'Request failed');
  }

  return response.json();
}

/**
 * Make API request with FormData (for file uploads)
 */
async function apiRequestFormData<T>(
  endpoint: string,
  formData: FormData
): Promise<T> {
  const url = `${API_URL}${endpoint}`;
  const token = getAuthToken();
  const headers: HeadersInit = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      detail: response.statusText || 'Request failed',
    }));
    throw new Error(error.detail || error.message || 'Request failed');
  }

  return response.json();
}

/**
 * Auth API methods
 */
const auth = {
  async register(data: { email: string; password: string; role: string }) {
    const response = await apiRequest<{
      user_id: string;
      email: string;
      role: string;
      wallet_address: string;
      access_token: string;
    }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    
    // Store token
    if (typeof window !== 'undefined' && response.access_token) {
      localStorage.setItem('auth_token', response.access_token);
      localStorage.setItem('user_role', response.role);
    }
    
    return response;
  },

  async login(data: { email: string; password: string }) {
    const response = await apiRequest<{
      user_id: string;
      email: string;
      role: string;
      wallet_address?: string;
      access_token: string;
    }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    
    // Store token
    if (typeof window !== 'undefined' && response.access_token) {
      localStorage.setItem('auth_token', response.access_token);
      localStorage.setItem('user_role', response.role);
    }
    
    return response;
  },

  async me() {
    return apiRequest<{
      user_id: string;
      email: string;
      role: string;
      wallet_address?: string;
    }>('/auth/me');
  },

  async getWallet() {
    return apiRequest<{
      wallet_address: string;
      circle_wallet_id: string;
      wallet_set_id?: string;
      blockchain?: string;
      balance?: any;
    }>('/auth/wallet');
  },

  logout() {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_role');
    }
  },
};

/**
 * Claims API methods
 */
const claims = {
  async create(data: { claim_amount: number; files?: File[] }) {
    const formData = new FormData();
    formData.append('claim_amount', data.claim_amount.toString());
    
    if (data.files && data.files.length > 0) {
      data.files.forEach((file) => {
        formData.append('files', file);
      });
    }
    
    return apiRequestFormData<{
      claim_id: string;
      status: string;
    }>('/claims', formData);
  },

  async get(claimId: string) {
    return apiRequest<any>(`/claims/${claimId}`);
  },

  async list() {
    return apiRequest<any[]>('/claims');
  },
};

/**
 * Agent API methods
 */
const agent = {
  async evaluate(claimId: string) {
    return apiRequest<{
      claim_id: string;
      decision: string;
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
      tool_calls?: Array<{
        tool_name: string;
        status: string;
        cost?: number;
        timestamp?: string;
      }>;
    }>(`/agent/evaluate/${claimId}`, {
      method: 'POST',
    });
  },

  async getResults(claimId: string) {
    return apiRequest<{
      claim_id: string;
      agent_results: Array<{
        agent_type: string;
        result: any;
        confidence?: number;
        created_at: string;
      }>;
    }>(`/agent/results/${claimId}`);
  },

  async getLogs(claimId: string) {
    return apiRequest<{
      claim_id: string;
      logs: Array<{
        id: string;
        claim_id: string;
        agent_type: string;
        message: string;
        log_level: string;
        metadata?: any;
        created_at: string;
      }>;
    }>(`/agent/logs/${claimId}`);
  },

  async getStatus(claimId: string) {
    return apiRequest<{
      claim_id: string;
      status: string;
      completed_agents: string[];
      pending_agents: string[];
      progress_percentage: number;
    }>(`/agent/status/${claimId}`);
  },
};

/**
 * Blockchain API methods
 */
const blockchain = {
  async settle(claimId: string) {
    return apiRequest<{
      claim_id: string;
      tx_hash: string;
      status: string;
    }>(`/blockchain/settle/${claimId}`, {
      method: 'POST',
    });
  },
};

/**
 * API client export
 */
export const api = {
  auth,
  claims,
  agent,
  blockchain,
};
