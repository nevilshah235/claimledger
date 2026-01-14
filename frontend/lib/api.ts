import { 
  Claim, 
  ClaimCreateResponse, 
  EvaluationResult, 
  SettlementResult,
  ApiError,
  HealthResponse,
  ApiInfo
} from './types';

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Generic fetch wrapper with error handling
async function fetchAPI<T>(
  endpoint: string, 
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Accept': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error: ApiError = await response.json().catch(() => ({ 
      detail: `HTTP ${response.status}: ${response.statusText}` 
    }));
    throw new Error(error.detail);
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
    // Create a new claim
    create: async (data: {
      claimant_address: string;
      claim_amount: number;
      files?: File[];
    }): Promise<ClaimCreateResponse> => {
      const formData = new FormData();
      formData.append('claimant_address', data.claimant_address);
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

  // Authentication (Circle Wallets)
  auth: {
    // Initialize Circle authentication
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

    // Complete Circle authentication
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

    // Get wallet address for authenticated user
    getWallet: async (userToken: string): Promise<{
      wallet_address: string;
      user_id: string;
    }> => {
      return fetchAPI('/auth/circle/wallet', {
        headers: {
          'X-User-Token': userToken,
        },
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
