/**
 * End-to-end tests for agent flow UI components
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { ClaimStatus } from '@/app/components/ClaimStatus';
import { SummaryCard } from '@/app/components/SummaryCard';
import { AgentResultsBreakdown } from '@/app/components/AgentResultsBreakdown';
import { ReviewReasonsList } from '@/app/components/ReviewReasonsList';
import { EvaluationProgress } from '@/app/components/EvaluationProgress';
import { DataRequestCard } from '@/app/components/DataRequestCard';
import { Claim, Decision } from '@/lib/types';
import { api } from '@/lib/api';

// Mock the API
jest.mock('@/lib/api', () => ({
  api: {
    agent: {
      evaluate: jest.fn(),
      getResults: jest.fn(),
      getStatus: jest.fn(),
    },
    claims: {
      get: jest.fn(),
    },
  },
}));

const mockApi = api as jest.Mocked<typeof api>;

describe('Agent Flow E2E Tests', () => {
  const mockClaim: Claim = {
    id: 'test-claim-123',
    claimant_address: '0x1234567890abcdef1234567890abcdef12345678',
    claim_amount: 1250.00,
    status: 'SUBMITTED',
    decision: null,
    confidence: null,
    approved_amount: null,
    processing_costs: null,
    tx_hash: null,
    created_at: new Date().toISOString(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('ClaimStatus Component', () => {
    it('should display claim information', () => {
      const onUpdate = jest.fn();
      render(<ClaimStatus claim={mockClaim} onUpdate={onUpdate} />);

      expect(screen.getByText(/Claim #test-claim/i)).toBeInTheDocument();
      expect(screen.getByText(/\$1,250.00/)).toBeInTheDocument();
    });

    it('should trigger evaluation when button is clicked', async () => {
      const onUpdate = jest.fn();
      const updatedClaim = { ...mockClaim, status: 'EVALUATING' as const };
      
      mockApi.agent.evaluate.mockResolvedValue({
        claim_id: mockClaim.id,
        decision: 'NEEDS_REVIEW' as Decision,
        confidence: 0.75,
        approved_amount: null,
        reasoning: 'Test reasoning',
        processing_costs: 0,
      });
      
      mockApi.claims.get.mockResolvedValue(updatedClaim);

      render(<ClaimStatus claim={mockClaim} onUpdate={onUpdate} />);

      const evaluateButton = screen.getByText(/Trigger AI Evaluation/i);
      fireEvent.click(evaluateButton);

      await waitFor(() => {
        expect(mockApi.agent.evaluate).toHaveBeenCalledWith(mockClaim.id);
      });
    });

    it('should show evaluation progress when status is EVALUATING', async () => {
      const evaluatingClaim = { ...mockClaim, status: 'EVALUATING' as const };
      const onUpdate = jest.fn();

      mockApi.agent.getStatus.mockResolvedValue({
        claim_id: mockClaim.id,
        status: 'EVALUATING',
        completed_agents: ['document'],
        pending_agents: ['image', 'fraud', 'reasoning'],
        progress_percentage: 25,
      });

      render(<ClaimStatus claim={evaluatingClaim} onUpdate={onUpdate} />);

      await waitFor(() => {
        expect(screen.getByText(/Evaluation in Progress/i)).toBeInTheDocument();
      });
    });

    it('should toggle between summary and detailed views', () => {
      const evaluatedClaim: Claim = {
        ...mockClaim,
        status: 'NEEDS_REVIEW',
        decision: 'NEEDS_REVIEW',
        confidence: 0.72,
      };
      const onUpdate = jest.fn();

      render(<ClaimStatus claim={evaluatedClaim} onUpdate={onUpdate} />);

      const summaryButton = screen.getByText('Summary');
      const detailedButton = screen.getByText('Detailed');

      expect(summaryButton).toBeInTheDocument();
      expect(detailedButton).toBeInTheDocument();

      fireEvent.click(detailedButton);
      // Detailed view should show agent results breakdown
      expect(mockApi.agent.getResults).toHaveBeenCalled();
    });
  });

  describe('SummaryCard Component', () => {
    it('should display confidence score', () => {
      render(
        <SummaryCard
          confidence={0.85}
          decision="APPROVED_WITH_REVIEW"
          summary="Test summary"
        />
      );

      expect(screen.getByText(/85%/)).toBeInTheDocument();
    });

    it('should display decision badge', () => {
      render(
        <SummaryCard
          confidence={0.95}
          decision="AUTO_APPROVED"
          summary="Auto-approved"
        />
      );

      expect(screen.getByText(/Auto-Approved/i)).toBeInTheDocument();
    });

    it('should show human review required badge', () => {
      render(
        <SummaryCard
          confidence={0.87}
          decision="APPROVED_WITH_REVIEW"
          humanReviewRequired={true}
        />
      );

      expect(screen.getByText(/Human Review Required/i)).toBeInTheDocument();
    });
  });

  describe('AgentResultsBreakdown Component', () => {
    it('should fetch and display agent results', async () => {
      mockApi.agent.getResults.mockResolvedValue({
        claim_id: 'test-claim-123',
        agent_results: [
          {
            agent_type: 'document',
            result: { summary: 'Document verified', valid: true },
            confidence: 0.85,
            created_at: new Date().toISOString(),
          },
        ],
      });

      render(<AgentResultsBreakdown claimId="test-claim-123" />);

      await waitFor(() => {
        expect(mockApi.agent.getResults).toHaveBeenCalledWith('test-claim-123');
      });

      await waitFor(() => {
        expect(screen.getByText(/Document Agent/i)).toBeInTheDocument();
      });
    });

    it('should expand agent cards to show details', async () => {
      mockApi.agent.getResults.mockResolvedValue({
        claim_id: 'test-claim-123',
        agent_results: [
          {
            agent_type: 'document',
            result: { 
              summary: 'Document verified',
              extracted_data: { invoice_number: '#12345' }
            },
            confidence: 0.85,
            created_at: new Date().toISOString(),
          },
        ],
      });

      render(<AgentResultsBreakdown claimId="test-claim-123" />);

      await waitFor(() => {
        expect(screen.getByText(/Document Agent/i)).toBeInTheDocument();
      });

      const expandButton = screen.getByRole('button');
      fireEvent.click(expandButton);

      await waitFor(() => {
        expect(screen.getByText(/Document verified/i)).toBeInTheDocument();
      });
    });
  });

  describe('ReviewReasonsList Component', () => {
    it('should display review reasons', () => {
      render(
        <ReviewReasonsList
          reviewReasons={['Minor contradictions detected', 'Image quality concerns']}
          humanReviewRequired={true}
        />
      );

      expect(screen.getByText(/Review Reasons/i)).toBeInTheDocument();
      expect(screen.getByText(/Minor contradictions detected/i)).toBeInTheDocument();
      expect(screen.getByText(/Human Review Required/i)).toBeInTheDocument();
    });

    it('renders nothing when no review reasons or contradictions', () => {
      const { container } = render(
        <ReviewReasonsList
          reviewReasons={null}
          contradictions={null}
          humanReviewRequired={true}
        />
      );

      expect(container.firstChild).toBeNull();
    });

    it('should display contradictions when provided', () => {
      render(
        <ReviewReasonsList
          reviewReasons={['Low confidence']}
          contradictions={['Claim amount (400.0 USD) does not match the extracted total (515.12 USD).']}
          humanReviewRequired={true}
        />
      );

      expect(screen.getByText(/Review Reasons/i)).toBeInTheDocument();
      expect(screen.getByText(/Low confidence/i)).toBeInTheDocument();
      expect(screen.getByText(/Contradictions/i)).toBeInTheDocument();
      expect(screen.getByText(/Claim amount \(400.0 USD\) does not match/i)).toBeInTheDocument();
    });
  });

  describe('EvaluationProgress Component', () => {
    it('should poll for status updates', async () => {
      mockApi.agent.getStatus.mockResolvedValue({
        claim_id: 'test-claim-123',
        status: 'EVALUATING',
        completed_agents: ['document'],
        pending_agents: ['image', 'fraud', 'reasoning'],
        progress_percentage: 25,
      });

      render(<EvaluationProgress claimId="test-claim-123" />);

      await waitFor(() => {
        expect(mockApi.agent.getStatus).toHaveBeenCalledWith('test-claim-123');
      });

      expect(screen.getByText(/Evaluation in Progress/i)).toBeInTheDocument();
      expect(screen.getByText(/25%/)).toBeInTheDocument();
    });
  });

  describe('DataRequestCard Component', () => {
    it('should display requested data types', () => {
      render(
        <DataRequestCard
          claimId="test-claim-123"
          requestedData={['document', 'image']}
        />
      );

      expect(screen.getByText(/Additional Evidence Required/i)).toBeInTheDocument();
      expect(screen.getByText(/Document/i)).toBeInTheDocument();
      expect(screen.getByText(/Image/i)).toBeInTheDocument();
    });

    it('should allow file upload', () => {
      render(
        <DataRequestCard
          claimId="test-claim-123"
          requestedData={['document']}
        />
      );

      const fileInput = screen.getByLabelText(/Upload Additional Files/i);
      expect(fileInput).toBeInTheDocument();
    });
  });
});
