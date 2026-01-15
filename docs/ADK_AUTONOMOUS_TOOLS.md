# ADK Autonomous Tool Calling & Human-in-the-Loop

## Overview

The ADK agents now autonomously call Circle payment tools and make decisions based on confidence thresholds, with human-in-the-loop support and data request capabilities.

## Key Features

### 1. Autonomous Tool Calling

Agents can now autonomously call Circle payment tools:
- **verify_document(claim_id, document_path)** - $0.10 USDC via x402
- **verify_image(claim_id, image_path)** - $0.15 USDC via x402
- **verify_fraud(claim_id)** - $0.10 USDC via x402
- **approve_claim(claim_id, amount, recipient)** - On-chain settlement

Tools are registered with all ADK agents and can be called autonomously during evaluation.

### 2. Confidence-Based Decision Making

The orchestrator agent makes decisions based on confidence thresholds:

| Confidence | Decision | Action |
|------------|----------|--------|
| >= 0.95 + no contradictions + fraud_risk < 0.3 | `AUTO_APPROVED` | Auto-approve and settle on-chain |
| >= 0.85 + no major contradictions | `APPROVED_WITH_REVIEW` | Approve but require human confirmation |
| >= 0.70 | `NEEDS_REVIEW` | Require human review |
| >= 0.50 | `NEEDS_MORE_DATA` | Request additional evidence |
| < 0.50 | `INSUFFICIENT_DATA` | Request more data or manual investigation |

### 3. Human-in-the-Loop

- **human_review_required** flag indicates when human review is needed
- **review_reasons** array explains why review is required
- Status transitions:
  - `AUTO_APPROVED` → `APPROVED` → `SETTLED` (if auto-settled)
  - `APPROVED_WITH_REVIEW` → `APPROVED` (awaiting human confirmation)
  - `NEEDS_REVIEW` → `NEEDS_REVIEW` (human must review)
  - `NEEDS_MORE_DATA` / `INSUFFICIENT_DATA` → `AWAITING_DATA`

### 4. Data Request Capability

Agents can request additional data when evidence is insufficient:
- **requested_data** field lists types of evidence needed (e.g., `["document", "image"]`)
- Status set to `AWAITING_DATA` when more data is needed
- Claimant can submit additional evidence to continue evaluation

## Architecture

### Orchestrator Agent

New `ADKOrchestratorAgent` class:
- Autonomously calls verification tools
- Makes decisions based on confidence thresholds
- Handles tool results and correlates evidence
- Returns structured decision with reasoning

### Updated Models

`Claim` model now includes:
- `requested_data` (JSON) - Types of additional data requested
- `human_review_required` (Boolean) - Human-in-the-loop flag
- `decision` - Extended to support new decision types
- `status` - Extended to support `AWAITING_DATA`

### API Response

`EvaluationResponse` now includes:
- `requested_data` - List of data types requested
- `human_review_required` - Boolean flag
- `decision` - One of: `AUTO_APPROVED`, `APPROVED_WITH_REVIEW`, `NEEDS_REVIEW`, `NEEDS_MORE_DATA`, `INSUFFICIENT_DATA`

## Workflow

### 1. Claim Submission
```
Claimant submits claim with evidence
→ Status: SUBMITTED
```

### 2. Agent Evaluation
```
Orchestrator agent:
1. Calls verify_document (if documents available)
2. Calls verify_image (if images available)
3. Calls verify_fraud (always)
4. Analyzes results and calculates confidence
5. Makes decision based on thresholds
```

### 3. Decision Outcomes

**High Confidence (>= 0.95)**
```
→ Decision: AUTO_APPROVED
→ Calls approve_claim tool
→ Status: APPROVED → SETTLED
→ Auto-settled on blockchain
```

**Medium-High Confidence (>= 0.85)**
```
→ Decision: APPROVED_WITH_REVIEW
→ Status: APPROVED
→ human_review_required: true
→ Human must confirm before settlement
```

**Medium Confidence (>= 0.70)**
```
→ Decision: NEEDS_REVIEW
→ Status: NEEDS_REVIEW
→ human_review_required: true
→ Human must review and decide
```

**Low Confidence (>= 0.50)**
```
→ Decision: NEEDS_MORE_DATA
→ Status: AWAITING_DATA
→ requested_data: ["document", "image"]
→ Claimant can submit additional evidence
```

**Very Low Confidence (< 0.50)**
```
→ Decision: INSUFFICIENT_DATA
→ Status: AWAITING_DATA
→ requested_data: [list of needed evidence]
→ May require manual investigation
```

## Tool Integration

### Circle Gateway Integration

All verification tools use Circle Gateway for micropayments:
- **X402Client** handles HTTP 402 Payment Required responses
- **GatewayService** creates micropayments via Circle Gateway API
- Payments are automatic - agents don't need to handle payment logic

### Payment Flow

```
Agent calls tool
→ Tool calls X402Client
→ X402Client detects 402 response
→ GatewayService creates micropayment
→ Payment receipt sent with retry
→ Tool returns results
```

## Agent Instructions

All agents have updated instructions that:
- Explicitly mention available tools
- Encourage tool usage for verification
- Explain that payments are handled automatically
- Guide agents to combine tool results with their own analysis

## Testing

To test autonomous tool calling:

1. **High Confidence Test**
   - Submit claim with complete evidence
   - Agent should call all tools
   - Should auto-approve if confidence >= 0.95

2. **Human Review Test**
   - Submit claim with partial evidence
   - Agent should request more data or flag for review

3. **Tool Calling Test**
   - Monitor tool calls during evaluation
   - Verify payments are processed via Circle Gateway

## Future Enhancements

- Add tool call retry logic
- Implement tool call caching
- Add tool usage analytics
- Support for additional verification tools
- Multi-step data request workflows
