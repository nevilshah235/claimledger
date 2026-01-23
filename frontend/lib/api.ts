import { 
  Claim, 
  ClaimCreateResponse, 
  EvaluationResult, 
  SettlementResult,
  ApiError,
  HealthResponse,
  ApiInfo,
  RegisterRequest,
  RegisterResponse,
  LoginRequest,
  LoginResponse,
  UserInfo,
  WalletInfo,
  AgentResultsResponse,
  EvaluationStatus,
  AgentLogsResponse
} from './types';

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Get auth token from localStorage
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('auth_token');
}

// Generic fetch wrapper with error handling and auth
async function fetchAPI<T>(
  endpoint: string, 
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getAuthToken();
  
  const headers: Record<string, string> = {
    'Accept': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };
  
  // Add auth token if available
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  // Ensure Content-Type is set for POST/PUT requests with JSON body
  if (options.body && typeof options.body === 'string' && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include',  // Include credentials for CORS
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const error: ApiError = await response.json();
      errorDetail = error.detail || errorDetail;
    } catch {
      // If response is not JSON, use status text
    }
    const error = new Error(errorDetail) as any;
    error.status = response.status;
    error.statusCode = response.status;
    throw error;
  }

  return response.json();
}

// ============================================
// API Client
// ============================================

export const api = {
  // Health & Info
  health: async (): Promise<HealthResponse> => {
    return fetchAPI<HealthResponse>('/health');
  },

  info: async (): Promise<ApiInfo> => {
    return fetchAPI<ApiInfo>('/');
  },

  // Claims
  claims: {
    // Create a new claim (uses authenticated user's wallet)
    create: async (data: {
      claim_amount: number;
      description?: string;
      files?: File[];
    }): Promise<ClaimCreateResponse> => {
      const formData = new FormData();
      formData.append('claim_amount', data.claim_amount.toString());
      if (data.description) {
        formData.append('description', data.description);
      }
      
      if (data.files) {
        data.files.forEach(file => {
          formData.append('files', file);
        });
      }

      return fetchAPI<ClaimCreateResponse>('/claims', {
        method: 'POST',
        body: formData,
      });
    },

    // Get claim by ID
    get: async (claimId: string): Promise<Claim> => {
      return fetchAPI<Claim>(`/claims/${claimId}`);
    },

    // List all claims (for insurer view)
    list: async (): Promise<Claim[]> => {
      // Note: This endpoint may need to be added to the backend
      // For now, we'll handle it client-side or add later
      return fetchAPI<Claim[]>('/claims');
    },

    requestData: async (claimId: string, requested_data: string[]): Promise<Claim> => {
      return fetchAPI<Claim>(`/claims/${claimId}/request-data`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requested_data }),
      });
    },

    overrideDecision: async (
      claimId: string,
      data: { decision: string; approved_amount?: number; summary?: string }
    ): Promise<Claim> => {
      return fetchAPI<Claim>(`/claims/${claimId}/override-decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
    },

    addEvidence: async (claimId: string, files: File[]): Promise<Claim> => {
      const formData = new FormData();
      files.forEach((file) => formData.append('files', file));

      return fetchAPI<Claim>(`/claims/${claimId}/evidence`, {
        method: 'POST',
        body: formData,
      });
    },

    // Get evidence files for a claim
    getEvidence: async (claimId: string): Promise<Array<{
      id: string;
      file_type: string;
      file_path: string;
      file_size: number | null;
      mime_type: string | null;
      created_at: string;
    }>> => {
      return fetchAPI(`/claims/${claimId}/evidence`);
    },

    // Download evidence file
    downloadEvidence: async (claimId: string, evidenceId: string): Promise<Blob> => {
      const url = `${API_BASE_URL}/claims/${claimId}/evidence/${evidenceId}/download`;
      const token = getAuthToken();
      
      const headers: Record<string, string> = {
        'Accept': '*/*',
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      const response = await fetch(url, {
        method: 'GET',
        headers,
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to download file: ${response.statusText}`);
      }

      return response.blob();
    },
  },

  // Agent Evaluation
  agent: {
    evaluate: async (claimId: string): Promise<EvaluationResult> => {
      return fetchAPI<EvaluationResult>(`/agent/evaluate/${claimId}`, {
        method: 'POST',
      });
    },

    // Get agent results for a claim
    getResults: async (claimId: string): Promise<AgentResultsResponse> => {
      return fetchAPI<AgentResultsResponse>(`/agent/results/${claimId}`);
    },

    // Get evaluation status for real-time progress
    getStatus: async (claimId: string): Promise<EvaluationStatus> => {
      return fetchAPI<EvaluationStatus>(`/agent/status/${claimId}`);
    },

    // Get agent activity logs
    getLogs: async (claimId: string): Promise<AgentLogsResponse> => {
      return fetchAPI<AgentLogsResponse>(`/agent/logs/${claimId}`);
    },

    chat: async (data: { message: string; role?: string; claim_id?: string | null }): Promise<{ reply: string }> => {
      return fetchAPI<{ reply: string }>('/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
    },
  },

  // Blockchain Settlement
  blockchain: {
    settle: async (claimId: string): Promise<SettlementResult> => {
      return fetchAPI<SettlementResult>(`/blockchain/settle/${claimId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });
    },

    getStatus: async (txHash: string): Promise<{
      tx_hash: string;
      status: string;
      block_number: number;
      explorer_url: string;
    }> => {
      return fetchAPI(`/blockchain/status/${txHash}`);
    },
  },

  // Authentication (Our own auth system)
  auth: {
    // Register new user
    register: async (data: RegisterRequest): Promise<RegisterResponse> => {
      const response = await fetchAPI<RegisterResponse>('/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      
      // Store token
      if (typeof window !== 'undefined') {
        localStorage.setItem('auth_token', response.access_token);
        localStorage.setItem('user_id', response.user_id);
        localStorage.setItem('user_role', response.role);
      }
      
      return response;
    },

    // Login user
    login: async (data: LoginRequest): Promise<LoginResponse> => {
      const response = await fetchAPI<LoginResponse>('/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      
      // Store token
      if (typeof window !== 'undefined') {
        localStorage.setItem('auth_token', response.access_token);
        localStorage.setItem('user_id', response.user_id);
        localStorage.setItem('user_role', response.role);
      }
      
      return response;
    },

    // Get current user info
    me: async (): Promise<UserInfo> => {
      return fetchAPI<UserInfo>('/auth/me');
    },

    // Logout (clear token)
    logout: (): void => {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_id');
        localStorage.removeItem('user_role');
      }
    },

    // Get wallet info
    getWallet: async (): Promise<WalletInfo> => {
      return fetchAPI<WalletInfo>('/auth/wallet');
    },

    // Admin auto-login
    adminLogin: async (): Promise<LoginResponse> => {
      const response = await fetchAPI<LoginResponse>('/auth/admin/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      // Store token
      if (typeof window !== 'undefined') {
        localStorage.setItem('auth_token', response.access_token);
        localStorage.setItem('user_id', response.user_id);
        localStorage.setItem('user_role', response.role);
      }
      
      return response;
    },

    // Legacy Circle endpoints (deprecated, kept for backward compatibility)
    initCircle: async (userId?: string): Promise<{
      user_id: string;
      user_token: string;
      challenge_id: string;
      app_id: string;
    }> => {
      return fetchAPI('/auth/circle/init', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: userId || null }),
      });
    },

    completeCircle: async (data: {
      user_token: string;
      wallet_address: string;
      circle_wallet_id?: string;
    }): Promise<{
      success: boolean;
      wallet_address: string;
      user_id: string;
    }> => {
      return fetchAPI('/auth/circle/complete', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
    },

    // Circle User-Controlled connect (Web SDK)
    circleConnectInit: async (): Promise<{
      available: boolean;
      app_id?: string | null;
      user_token?: string | null;
      encryption_key?: string | null;
      challenge_id?: string | null;
      message?: string | null;
    }> => {
      return fetchAPI('/auth/circle/connect/init', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
    },

    circleConnectComplete: async (): Promise<{
      success: boolean;
      wallet_address?: string | null;
      circle_wallet_id?: string | null;
    }> => {
      return fetchAPI('/auth/circle/connect/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
    },

    circleConnectStatus: async (): Promise<{
      user_id: string;
      user_email: string;
      circle_wallets: Array<any>;
      db_wallet: {
        wallet_address: string;
        circle_wallet_id: string;
        wallet_set_id?: string;
      } | null;
      has_circle_wallet: boolean;
      has_db_wallet: boolean;
      mismatch?: boolean;
      mismatch_details?: string;
      error?: string;
    }> => {
      return fetchAPI('/auth/circle/connect/status', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
    },

    // Admin auto-login
    adminLogin: async (): Promise<LoginResponse> => {
      try {
        const response = await fetchAPI<LoginResponse>('/auth/admin/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        });
        
        // Store token
        if (typeof window !== 'undefined') {
          localStorage.setItem('auth_token', response.access_token);
          localStorage.setItem('user_id', response.user_id);
          localStorage.setItem('user_role', response.role);
        }
        
        return response;
      } catch (error: any) {
        // Clear any partial token storage on error
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth_token');
          localStorage.removeItem('user_id');
          localStorage.removeItem('user_role');
        }
        throw error; // Re-throw to let caller handle
      }
    },
  },

  // Verifiers (x402)
  verifier: {
    document: async (claimId: string, documentPath: string, receipt?: string) => {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (receipt) {
        headers['X-Payment-Receipt'] = receipt;
      }

      return fetchAPI('/verifier/document', {
        method: 'POST',
        headers,
        body: JSON.stringify({ claim_id: claimId, document_path: documentPath }),
      });
    },

    image: async (claimId: string, imagePath: string, receipt?: string) => {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (receipt) {
        headers['X-Payment-Receipt'] = receipt;
      }

      return fetchAPI('/verifier/image', {
        method: 'POST',
        headers,
        body: JSON.stringify({ claim_id: claimId, image_path: imagePath }),
      });
    },

    fraud: async (claimId: string, receipt?: string) => {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (receipt) {
        headers['X-Payment-Receipt'] = receipt;
      }

      return fetchAPI('/verifier/fraud', {
        method: 'POST',
        headers,
        body: JSON.stringify({ claim_id: claimId }),
      });
    },
  },

  // Admin endpoints
  admin: {
    getFees: async (): Promise<{
      wallet_address: string | null;
      current_balance: number | null;
      total_spent: number;
      total_evaluations: number;
      average_cost_per_evaluation: number;
      fee_breakdown: Array<{
        claim_id: string;
        total_cost: number;
        tool_costs: Record<string, number>;
        timestamp: string;
      }>;
    }> => {
      return fetchAPI('/admin/fees');
    },
  },
};

// Export individual functions for convenience
export const { health, info, claims, agent, blockchain, verifier, auth, admin } = api;

export default api;
