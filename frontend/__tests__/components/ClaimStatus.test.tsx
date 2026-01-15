/**
 * Tests for ClaimStatus component.
 */

import { render, screen } from '@testing-library/react';
import { ClaimStatus } from '@/app/components/ClaimStatus';

describe('ClaimStatus', () => {
  const mockClaim = {
    id: 'claim-123',
    claimant_address: '0x123',
    claim_amount: 1000,
    status: 'SUBMITTED',
    decision: null,
    confidence: null,
    approved_amount: null,
    processing_costs: null,
    tx_hash: null,
    created_at: new Date().toISOString(),
  };

  it('should render claim status', () => {
    render(<ClaimStatus claim={mockClaim} />);

    expect(screen.getByText(/claim-123/i)).toBeInTheDocument();
    expect(screen.getByText(/submitted/i)).toBeInTheDocument();
  });

  it('should display approved status with amount', () => {
    const approvedClaim = {
      ...mockClaim,
      status: 'APPROVED',
      decision: 'APPROVED',
      confidence: 0.92,
      approved_amount: 1000,
    };

    render(<ClaimStatus claim={approvedClaim} />);

    expect(screen.getByText(/approved/i)).toBeInTheDocument();
    expect(screen.getByText(/\$1,000/i)).toBeInTheDocument();
  });

  it('should display settled status with tx hash', () => {
    const settledClaim = {
      ...mockClaim,
      status: 'SETTLED',
      tx_hash: '0xabcdef1234567890',
    };

    render(<ClaimStatus claim={settledClaim} />);

    expect(screen.getByText(/settled/i)).toBeInTheDocument();
    expect(screen.getByText(/0xabcdef/i)).toBeInTheDocument();
  });

  it('should display processing costs', () => {
    const claimWithCosts = {
      ...mockClaim,
      processing_costs: 0.35,
    };

    render(<ClaimStatus claim={claimWithCosts} />);

    expect(screen.getByText(/\$0.35/i)).toBeInTheDocument();
  });
});
