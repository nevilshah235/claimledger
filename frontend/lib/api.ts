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
  WalletInfo
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
    throw new Error(errorDetail);
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
      files?: File[];
    }): Promise<ClaimCreateResponse> => {
      const formData = new FormData();
      formData.append('claim_amount', data.claim_amount.toString());
      
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
  },

  // Agent Evaluation
  agent: {
    evaluate: async (claimId: string): Promise<EvaluationResult> => {
      return fetchAPI<EvaluationResult>(`/agent/evaluate/${claimId}`, {
        method: 'POST',
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
};

// Export individual functions for convenience
export const { health, info, claims, agent, blockchain, verifier, auth } = api;

export default api;
