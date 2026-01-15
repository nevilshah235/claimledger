/**
 * Tests for ClaimForm component.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ClaimForm } from '@/app/components/ClaimForm';
import { api } from '@/lib/api';

jest.mock('@/lib/api');

describe('ClaimForm', () => {
  const mockOnSuccess = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render claim form', () => {
    render(<ClaimForm onSuccess={mockOnSuccess} walletAddress="0x123" />);

    expect(screen.getByLabelText(/claim amount/i)).toBeInTheDocument();
    // File input is hidden, so check for the label text instead
    expect(screen.getByText(/evidence files/i)).toBeInTheDocument();
    expect(screen.getByTestId('file-input')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /submit claim/i })).toBeInTheDocument();
  });

  it('should submit claim with amount and files', async () => {
    const mockCreate = jest.fn().mockResolvedValue({
      claim_id: 'claim-123',
      status: 'SUBMITTED',
    });

    (api.claims.create as jest.Mock) = mockCreate;

    render(<ClaimForm onSuccess={mockOnSuccess} walletAddress="0x123" />);

    const amountInput = screen.getByLabelText(/claim amount/i);
    const fileInput = screen.getByTestId('file-input') as HTMLInputElement;
    const submitButton = screen.getByRole('button', { name: /submit claim/i });

    await userEvent.type(amountInput, '1500');
    
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    await userEvent.upload(fileInput, file);

    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalled();
      expect(mockOnSuccess).toHaveBeenCalled();
    });
  });

  it('should display error on submission failure', async () => {
    const mockCreate = jest.fn().mockRejectedValue(new Error('Submission failed'));

    (api.claims.create as jest.Mock) = mockCreate;

    render(<ClaimForm onSuccess={mockOnSuccess} walletAddress="0x123" />);

    const amountInput = screen.getByLabelText(/claim amount/i);
    const submitButton = screen.getByRole('button', { name: /submit claim/i });

    await userEvent.type(amountInput, '1500');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/submission failed/i)).toBeInTheDocument();
    });
  });

  it('should validate required fields', async () => {
    render(<ClaimForm onSuccess={mockOnSuccess} walletAddress="0x123" />);

    const submitButton = screen.getByRole('button', { name: /submit claim/i });
    await userEvent.click(submitButton);

    // HTML5 validation should prevent submission
    expect(api.claims.create).not.toHaveBeenCalled();
  });
});
