/**
 * Tests for insurer page.
 */

import { render, screen } from '@testing-library/react';
import InsurerPage from '@/app/insurer/page';

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

jest.mock('@/lib/api', () => ({
  api: {
    claims: {
      list: jest.fn().mockResolvedValue([
        {
          id: 'claim-1',
          status: 'SUBMITTED',
          claim_amount: 1000,
        },
      ]),
    },
    agent: {
      evaluate: jest.fn(),
    },
    blockchain: {
      settle: jest.fn(),
    },
  },
}));

describe('InsurerPage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should render login prompt when not authenticated', () => {
    render(<InsurerPage />);
    expect(screen.getByTestId('auth-modal')).toBeInTheDocument();
  });

  it('should render claims list when authenticated', async () => {
    localStorage.setItem('auth_token', 'token-123');
    localStorage.setItem('user_role', 'insurer');

    render(<InsurerPage />);
    
    // Wait for claims to load
    await screen.findByTestId('claim-status');
    expect(screen.getByTestId('claim-status')).toBeInTheDocument();
  });
});
