/**
 * Tests for insurer page.
 */

import { render, screen, waitFor } from '@testing-library/react';
import InsurerPage from '@/app/insurer/page';

// Mock the API module first, before any imports
const mockApi = {
  claims: {
    list: jest.fn(),
    get: jest.fn(),
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
      {isOpen && <button onClick={() => onSuccess('0x456', 'insurer')}>Mock Login</button>}
    </div>
  ),
}));

jest.mock('@/app/components/ClaimStatus', () => ({
  ClaimStatus: ({ claim }: any) => <div data-testid="claim-status">{claim.id}</div>,
}));

jest.mock('@/app/components/Navbar', () => ({
  Navbar: ({ walletAddress, role, onConnect, onDisconnect }: any) => (
    <nav data-testid="navbar">
      <div>Navbar</div>
      {walletAddress && <div data-testid="wallet-address">{walletAddress}</div>}
    </nav>
  ),
}));

jest.mock('@/app/components/SettlementCard', () => ({
  SettlementCard: ({ claim }: any) => (
    <div data-testid="settlement-card">{claim.id}</div>
  ),
}));

describe('InsurerPage', () => {
  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
    
    // Reset API mocks
    mockApi.claims.list.mockResolvedValue([
      {
        id: 'claim-1',
        claimant_address: '0x1234567890ABCDEF1234567890ABCDEF12345678',
        claim_amount: 1000,
        status: 'SUBMITTED',
        decision: null,
        confidence: null,
        approved_amount: null,
        processing_costs: null,
        tx_hash: null,
        created_at: new Date().toISOString(),
      },
    ]);
    mockApi.auth.logout.mockImplementation(() => {});
  });

  it('should render login prompt when not authenticated', async () => {
    mockApi.auth.me.mockRejectedValue(new Error('Not authenticated'));
    
    render(<InsurerPage />);
    
    await waitFor(() => {
      expect(screen.getByTestId('auth-modal')).toBeInTheDocument();
    });
  });

  it('should render claims list when authenticated', async () => {
    localStorage.setItem('auth_token', 'token-123');
    localStorage.setItem('user_role', 'insurer');

    mockApi.auth.me.mockResolvedValue({
      user_id: 'user-123',
      email: 'test@example.com',
      role: 'insurer',
      wallet_address: '0x123',
    });

    render(<InsurerPage />);
    
    // Wait for claims to load - the page renders SettlementCard components
    await screen.findByTestId('settlement-card');
    expect(screen.getByTestId('settlement-card')).toBeInTheDocument();
  });
});
