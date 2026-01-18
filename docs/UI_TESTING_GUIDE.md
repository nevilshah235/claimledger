# UI Testing Guide - Agentic Flow Features

## Quick Start

Both servers should be running:
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000

Open http://localhost:3000 in your browser to begin testing.

## Testing Checklist

### 1. Claim Submission Flow

#### Test: Create a New Claim
1. Navigate to `/claimant` page
2. Connect wallet (or register/login)
3. Fill out claim form:
   - Enter claim amount (e.g., $1,250.00)
   - Upload at least one file (document or image)
4. Submit claim
5. **Expected**: Claim appears with status "SUBMITTED"

### 2. Real-Time Evaluation Progress

#### Test: Trigger Evaluation and Watch Progress
1. On the claim card, click "Trigger AI Evaluation"
2. **Expected**: 
   - Status changes to "EVALUATING"
   - `EvaluationProgress` component appears showing:
     - Progress bar (0% → 100%)
     - Agent execution status:
       - Document Agent: ⏳ → ✓
       - Image Agent: ⏳ → ✓
       - Fraud Agent: ⏳ → ✓
       - Reasoning Agent: ⏳ → ✓
     - Tool call costs displayed ($0.10, $0.15, $0.10)
     - Total cost accumulating
   - Auto-refreshes every 2 seconds

### 3. Summary View

#### Test: View Summary After Evaluation
1. Wait for evaluation to complete
2. **Expected**:
   - View defaults to "Summary" mode
   - `SummaryCard` displays:
     - Large confidence score (e.g., 96%) with color-coded bar
     - Decision badge (AUTO_APPROVED, NEEDS_REVIEW, etc.)
     - Comprehensive summary text
     - Approved amount (if approved)
     - Processing costs
     - Human review required badge (if applicable)

#### Test: Decision Type Badges
Test different decision types:
- **AUTO_APPROVED** (green) - High confidence, auto-settled
- **APPROVED_WITH_REVIEW** (yellow) - Needs human confirmation
- **NEEDS_REVIEW** (orange) - Requires manual review
- **NEEDS_MORE_DATA** (blue) - Request additional evidence
- **INSUFFICIENT_DATA** (red) - Critical issue

### 4. Detailed View

#### Test: Toggle to Detailed View
1. After evaluation completes, click "Detailed" tab
2. **Expected**:
   - `AgentResultsBreakdown` component displays:
     - Expandable cards for each agent:
       - 📄 Document Agent
       - 🖼️ Image Agent
       - 🛡️ Fraud Agent
       - 🧠 Reasoning Agent
     - Each card shows:
       - Confidence score with progress bar
       - Tool calls made (verify_document, verify_image, etc.)
       - x402 payment costs
       - Extracted data (when expanded)
       - Summary text

#### Test: Expand Agent Cards
1. Click on an agent card to expand
2. **Expected**:
   - Shows detailed information:
     - Tool call details with status
     - Extracted data (invoice numbers, amounts, etc.)
     - Damage assessment (for image agent)
     - Fraud score (for fraud agent)
     - Timestamp

### 5. Review Reasons

#### Test: View Review Reasons
1. Create a claim that results in NEEDS_REVIEW
2. **Expected**:
   - `ReviewReasonsList` component appears
   - Shows list of review reasons:
     - Minor contradictions
     - Image quality concerns
     - Fraud risk indicators
   - "Human Review Required" badge visible

### 6. Data Request Flow

#### Test: AWAITING_DATA Status
1. Create a claim with minimal evidence
2. Trigger evaluation
3. If confidence is low, **Expected**:
   - Status changes to "AWAITING_DATA"
   - `DataRequestCard` component appears:
     - Warning icon
     - List of requested data types (document, image, etc.)
     - File upload input
     - "Upload Additional Files" button

#### Test: Upload Additional Evidence
1. When `DataRequestCard` is shown:
   - Click file input
   - Select additional files
   - Click "Upload Additional Files"
2. **Expected**:
   - Files are uploaded (or shows success message)
   - Can re-trigger evaluation

### 7. Tool Call Visualization

#### Test: View Tool Calls
1. After evaluation, check summary or detailed view
2. **Expected**:
   - Tool calls section shows:
     - ✓ verify_document - $0.10 USDC
     - ✓ verify_image - $0.15 USDC
     - ✓ verify_fraud - $0.10 USDC
     - ✓ approve_claim - Settlement (if auto-approved)
   - Each tool call shows status (completed/pending/failed)

### 8. Settlement Flow

#### Test: Auto-Settlement
1. Create a claim with high confidence evidence
2. Trigger evaluation
3. **Expected**:
   - If confidence >= 0.95:
     - Decision: AUTO_APPROVED
     - Status: SETTLED (if auto-settled)
     - Transaction hash displayed
     - Link to blockchain explorer

### 9. Insurer View

#### Test: Insurer Dashboard
1. Navigate to `/insurer` page
2. Login as insurer
3. **Expected**:
   - Dashboard shows all claims
   - Filter by status
   - Claims show:
     - Confidence scores
     - Decision badges
     - Review status

#### Test: Insurer Review
1. Click on a claim with NEEDS_REVIEW status
2. **Expected**:
   - See full agent results breakdown
   - Review reasons displayed
   - Can approve/reject claim

### 10. Responsive Design

#### Test: Mobile View
1. Open browser DevTools
2. Toggle device toolbar (mobile view)
3. **Expected**:
   - All components stack vertically
   - Cards are full width
   - Buttons are touch-friendly
   - Text is readable

### 11. Error Handling

#### Test: Network Errors
1. Stop backend server
2. Try to trigger evaluation
3. **Expected**:
   - Error message displayed
   - UI doesn't crash
   - Can retry when backend is back

#### Test: Invalid Claim ID
1. Navigate to invalid claim URL
2. **Expected**:
   - Error message shown
   - Graceful fallback

## API Endpoint Testing

### Test Agent Results Endpoint
```bash
# Get agent results for a claim
curl http://localhost:8000/agent/results/{claim_id}

# Expected: JSON with agent_results array
```

### Test Evaluation Status Endpoint
```bash
# Get evaluation status
curl http://localhost:8000/agent/status/{claim_id}

# Expected: JSON with status, completed_agents, pending_agents, progress_percentage
```

### Test Enhanced Evaluation Response
```bash
# Trigger evaluation
curl -X POST http://localhost:8000/agent/evaluate/{claim_id}

# Expected: JSON includes:
# - agent_results (object)
# - tool_calls (array)
# - requested_data (array, if applicable)
# - human_review_required (boolean)
```

## Common Issues & Solutions

### Issue: Evaluation Progress Not Showing
**Solution**: 
- Check browser console for errors
- Verify backend is running
- Check network tab for API calls

### Issue: Agent Results Not Loading
**Solution**:
- Verify claim has been evaluated
- Check `/agent/results/{claim_id}` endpoint directly
- Verify database has agent_results records

### Issue: Tool Calls Not Displayed
**Solution**:
- Tool calls may be null if orchestrator doesn't return them
- Check evaluation response includes `tool_calls` field
- Fallback tool calls are inferred from agent results

### Issue: Toggle Not Working
**Solution**:
- Verify claim status is not SUBMITTED or EVALUATING
- Check browser console for errors
- Verify component state is updating

## Performance Testing

### Test: Multiple Concurrent Evaluations
1. Create multiple claims
2. Trigger evaluations simultaneously
3. **Expected**:
   - Each claim shows its own progress
   - No UI blocking
   - All evaluations complete successfully

### Test: Large Agent Results
1. Create claim with many evidence files
2. Trigger evaluation
3. **Expected**:
   - Detailed view loads all results
   - Expandable cards work smoothly
   - No performance degradation

## Browser Compatibility

Test in:
- ✅ Chrome/Edge (Chromium)
- ✅ Firefox
- ✅ Safari
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

## Next Steps

After testing:
1. Document any bugs found
2. Test edge cases (empty results, null values, etc.)
3. Verify all decision paths work
4. Test with real ADK orchestrator (not mocked)
5. Performance test with multiple users
