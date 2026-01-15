/**
 * Tests for claimant page.
 */

import { render, screen, waitFor } from '@testing-library/react';
import ClaimantPage from '@/app/claimant/page';

// Mock the API module first, before any imports
const mockApi = {
  claims: {
    get: jest.fn(),
    create: jest.fn(),
    list: jest.fn(),
  },
  agent: {
    evaluate: jest.fn(),
  },
  blockchain: {
    settle: jest.fn(),
  },
  auth: {
    me: jest.fn(),
    logout: jest.fn(),
    login: jest.fn(),
    register: jest.fn(),
    getWallet: jest.fn(),
  },
};

jest.mock('@/lib/api', () => ({
  api: mockApi,
}));

// Mock components
jest.mock('@/app/components/AuthModal', () => ({
  AuthModal: ({ isOpen, onClose, onSuccess }: any) => (
    <div data-testid="auth-modal">
      {isOpen && <button onClick={() => onSuccess('0x123', 'claimant')}>Mock Login</button>}
    </div>
  ),
}));

jest.mock('@/app/components/ClaimForm', () => ({
  ClaimForm: ({ onSuccess }: any) => (
    <div data-testid="claim-form">
      <button onClick={() => onSuccess()}>Submit Claim</button>
    </div>
  ),
}));

jest.mock('@/app/components/WalletDisplay', () => ({
  WalletDisplay: ({ address }: any) => <div data-testid="wallet-display">{address}</div>,
}));

describe('ClaimantPage', () => {
  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
    mockApi.auth.logout.mockImplementation(() => {});
  });

  it('should render login prompt when not authenticated', async () => {
    mockApi.auth.me.mockRejectedValue(new Error('Not authenticated'));
    
    render(<ClaimantPage />);
    
    await waitFor(() => {
      expect(screen.getByTestId('auth-modal')).toBeInTheDocument();
    });
  });

  it('should render claim form when authenticated', async () => {
    localStorage.setItem('auth_token', 'token-123');
    localStorage.setItem('user_role', 'claimant');
    localStorage.setItem('wallet_address', '0x123');

    mockApi.auth.me.mockResolvedValue({
      user_id: 'user-123',
      email: 'test@example.com',
      role: 'claimant',
      wallet_address: '0x123',
    });

    render(<ClaimantPage />);
    
    // Wait for async operations to complete
    await waitFor(() => {
      expect(screen.getByTestId('claim-form')).toBeInTheDocument();
    });
    
    // WalletDisplay should be rendered when walletAddress is set
    await waitFor(() => {
      expect(screen.getByTestId('wallet-display')).toBeInTheDocument();
    });
  });
});
