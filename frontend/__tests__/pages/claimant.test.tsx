/**
 * Tests for claimant page.
 */

import { render, screen } from '@testing-library/react';
import ClaimantPage from '@/app/claimant/page';

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
  });

  it('should render login prompt when not authenticated', () => {
    render(<ClaimantPage />);
    expect(screen.getByTestId('auth-modal')).toBeInTheDocument();
  });

  it('should render claim form when authenticated', () => {
    localStorage.setItem('auth_token', 'token-123');
    localStorage.setItem('user_role', 'claimant');
    localStorage.setItem('wallet_address', '0x123');

    render(<ClaimantPage />);
    expect(screen.getByTestId('claim-form')).toBeInTheDocument();
    expect(screen.getByTestId('wallet-display')).toBeInTheDocument();
  });
});
