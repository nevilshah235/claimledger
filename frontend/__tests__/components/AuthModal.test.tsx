/**
 * Tests for AuthModal component.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthModal } from '@/app/components/AuthModal';
import { api } from '@/lib/api';

jest.mock('@/lib/api');

describe('AuthModal', () => {
  const mockOnClose = jest.fn();
  const mockOnSuccess = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render login form when isLogin is true', () => {
    render(
      <AuthModal
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
        role="claimant"
      />
    );

    expect(screen.getByText(/login as claimant/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/your@email.com/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/••••••••/i)).toBeInTheDocument();
  });

  it('should render register form when isLogin is false', () => {
    render(
      <AuthModal
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
        role="insurer"
      />
    );

    // Click to switch to register
    const switchButton = screen.getByText(/don't have an account/i);
    userEvent.click(switchButton);

    expect(screen.getByText(/register as insurer/i)).toBeInTheDocument();
  });

  it('should call login API on form submit', async () => {
    const mockLogin = jest.fn().mockResolvedValue({
      user_id: 'user-123',
      email: 'test@example.com',
      role: 'claimant',
      wallet_address: '0x123',
      access_token: 'token-123',
    });

    (api.auth.login as jest.Mock) = mockLogin;

    render(
      <AuthModal
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
        role="claimant"
      />
    );

    const emailInput = screen.getByPlaceholderText(/your@email.com/i);
    const passwordInput = screen.getByPlaceholderText(/••••••••/i);
    const submitButton = screen.getByRole('button', { name: /login/i });

    await userEvent.type(emailInput, 'test@example.com');
    await userEvent.type(passwordInput, 'password123');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      });
      expect(mockOnSuccess).toHaveBeenCalledWith('0x123', 'claimant');
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  it('should call register API when in register mode', async () => {
    const mockRegister = jest.fn().mockResolvedValue({
      user_id: 'user-123',
      email: 'test@example.com',
      role: 'insurer',
      wallet_address: '0x456',
      access_token: 'token-123',
    });

    (api.auth.register as jest.Mock) = mockRegister;

    render(
      <AuthModal
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
        role="insurer"
      />
    );

    // Switch to register mode
    const switchButton = screen.getByText(/don't have an account/i);
    await userEvent.click(switchButton);

    const emailInput = screen.getByPlaceholderText(/your@email.com/i);
    const passwordInput = screen.getByPlaceholderText(/••••••••/i);
    const submitButton = screen.getByRole('button', { name: /register/i });

    await userEvent.type(emailInput, 'test@example.com');
    await userEvent.type(passwordInput, 'password123');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
        role: 'insurer',
      });
      expect(mockOnSuccess).toHaveBeenCalledWith('0x456', 'insurer');
    });
  });

  it('should display error message on API failure', async () => {
    const mockLogin = jest.fn().mockRejectedValue(new Error('Invalid credentials'));

    (api.auth.login as jest.Mock) = mockLogin;

    render(
      <AuthModal
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
        role="claimant"
      />
    );

    const emailInput = screen.getByPlaceholderText(/your@email.com/i);
    const passwordInput = screen.getByPlaceholderText(/••••••••/i);
    const submitButton = screen.getByRole('button', { name: /login/i });

    await userEvent.type(emailInput, 'test@example.com');
    await userEvent.type(passwordInput, 'wrongpassword');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
    });
  });

  it('should not render when isOpen is false', () => {
    render(
      <AuthModal
        isOpen={false}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
        role="claimant"
      />
    );

    expect(screen.queryByText(/login/i)).not.toBeInTheDocument();
  });
});
