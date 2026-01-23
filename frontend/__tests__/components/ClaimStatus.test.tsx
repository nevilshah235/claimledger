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

    // Claim ID is truncated to first 8 characters
    expect(screen.getByText(/claim-12/i)).toBeInTheDocument();
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

    // Use getAllByText since "Approved" appears multiple times (badge and label)
    const approvedTexts = screen.getAllByText(/approved/i);
    expect(approvedTexts.length).toBeGreaterThan(0);
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

  it('should not display processing costs (evaluations are free)', () => {
    const claimWithCosts = {
      ...mockClaim,
      processing_costs: 0,
    };

    render(<ClaimStatus claim={claimWithCosts} />);

    // No per-evaluation cost is shown; evaluations are free
    expect(screen.queryByText(/\$0\.35/i)).not.toBeInTheDocument();
  });
});
