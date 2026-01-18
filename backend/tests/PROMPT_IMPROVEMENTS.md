# Agent Prompt Improvements Plan

Based on test results, here are the identified issues and recommended improvements.

## Current Issues Identified

### 1. Incomplete Tool Calling ⚠️
**Issue**: Agent only calls `extract_document_data` but doesn't continue with:
- `estimate_repair_cost`
- `cross_check_amounts`
- `validate_claim_data`
- `verify_document`
- `verify_fraud`

**Root Cause**: Prompt may not be clear enough about the complete flow sequence.

**Impact**: 
- No amount validation happens
- No fraud detection
- No proper decision making
- Falls back to low confidence (50%)

### 2. JSON Response Format ⚠️
**Issue**: Agent response doesn't follow structured JSON format.

**Error**: `⚠ No valid JSON found in response, using text fallback`

**Root Cause**: Prompt doesn't enforce structured output format strongly enough.

**Impact**:
- Schema validation fails
- Fallback parsing used
- Less reliable decision making

### 3. Tool Validation Warnings ⚠️
**Warnings**:
- `verify_fraud was not called (required for all claims)`
- `verify_document was not called but 1 document(s) available`

**Root Cause**: Agent doesn't understand that these tools are required.

**Impact**: Incomplete evaluation, missing fraud detection.

## Recommended Prompt Improvements

### 1. Add Clear Tool Calling Sequence

```
**MANDATORY Tool Calling Sequence:**

Step 1: Extract Data (ALWAYS CALL FIRST)
- extract_document_data(claim_id, document_path) for EACH document
- extract_image_data(claim_id, image_path) for EACH image (if available)

Step 2: Estimate Costs (ALWAYS CALL AFTER EXTRACTION)
- estimate_repair_cost(claim_id, extracted_data, damage_assessment)
- cross_check_amounts(claim_id, claim_amount, extracted_total, estimated_cost, document_amount)

Step 3: Validate Claim (ALWAYS CALL AFTER COST ESTIMATION)
- validate_claim_data(claim_id, claim_amount, extracted_data, damage_assessment, cost_analysis, cross_check_result)

Step 4: Verify (ONLY IF VALIDATION PASSES)
- verify_document(claim_id, document_path) - REQUIRED if documents exist
- verify_image(claim_id, image_path) - REQUIRED if images exist  
- verify_fraud(claim_id) - ALWAYS REQUIRED

**IMPORTANT**: You MUST call ALL tools in sequence. Do NOT skip any step.
```

### 2. Add Amount Validation Instructions

```
**Amount Validation Process:**

1. Extract total_amount from extract_document_data result:
   - Look for: total_amount, grand_total, digit_liability + customer_liability
   - Use the highest matching amount found

2. Compare claim_amount with extracted total_amount:
   - Calculate difference: abs(claim_amount - extracted_total)
   - Calculate percentage: (difference / max(claim_amount, extracted_total)) * 100

3. Flag contradictions:
   - If difference > 20%: Add to contradictions list
   - If difference > 50%: Set fraud_risk >= 0.5

4. Use cross_check_amounts result:
   - Check "matches" field
   - If False: Add warnings to contradictions
   - Use "difference_percent" to determine severity
```

### 3. Add Structured Output Format

```
**REQUIRED Output Format (JSON only):**

{
  "decision": "AUTO_APPROVED" | "APPROVED_WITH_REVIEW" | "NEEDS_REVIEW" | "NEEDS_MORE_DATA" | "INSUFFICIENT_DATA" | "FRAUD_DETECTED",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of decision",
  "tool_results": {
    "extract_document_data": {...},
    "estimate_repair_cost": {...},
    "cross_check_amounts": {...},
    "validate_claim_data": {...},
    "verify_document": {...},
    "verify_fraud": {...}
  },
  "requested_data": ["image"] | [],
  "human_review_required": true | false,
  "review_reasons": ["reason1", "reason2"],
  "contradictions": ["contradiction1"],
  "fraud_risk": 0.0-1.0
}

**CRITICAL**: Return ONLY valid JSON. No markdown, no code blocks, no explanations outside JSON.
```

### 4. Add Fraud Detection Guidelines

```
**Fraud Detection Rules:**

High Fraud Risk (fraud_risk >= 0.7) → FRAUD_DETECTED:
- Amount mismatch > 50%
- Missing critical fields (policy_number, claim_number, dates)
- Invalid dates (future dates, dates after accident)
- Suspicious patterns (round numbers, unusual amounts)

Medium Fraud Risk (0.3 <= fraud_risk < 0.7) → NEEDS_REVIEW:
- Amount mismatch 20-50%
- Missing some fields
- Minor date inconsistencies

Low Fraud Risk (fraud_risk < 0.3) → Can auto-approve if confidence >= 0.95
```

### 5. Add Examples

```
**Example 1: Matching Amount, High Confidence**
1. extract_document_data → total_amount: 41370.65
2. cross_check_amounts → matches: true, difference: 0
3. validate_claim_data → recommendation: PROCEED
4. verify_document → valid: true
5. verify_fraud → fraud_score: 0.1
Decision: AUTO_APPROVED, confidence: 0.96

**Example 2: Mismatched Amount**
1. extract_document_data → total_amount: 41370.65
2. cross_check_amounts → matches: false, difference_percent: 50%
3. validate_claim_data → recommendation: REVIEW
4. verify_fraud → fraud_score: 0.6
Decision: NEEDS_REVIEW, confidence: 0.7, contradictions: ["Amount mismatch 50%"]
```

### 6. Reduce Prompt Length

**Current**: 137 lines
**Target**: ~50-60 lines

**Strategy**:
- Remove repetition
- Use examples instead of verbose explanations
- Focus on critical instructions
- Move detailed rules to code (already done)

## Implementation Plan

### Phase 1: Fix Tool Calling (High Priority)
1. Add clear sequence instructions
2. Add "MUST CALL" emphasis
3. Add examples of complete sequences

### Phase 2: Fix Output Format (High Priority)
1. Add structured JSON format requirement
2. Add "ONLY JSON" emphasis
3. Add validation instructions

### Phase 3: Improve Amount Validation (Medium Priority)
1. Add explicit extraction instructions
2. Add comparison logic
3. Add contradiction detection rules

### Phase 4: Enhance Fraud Detection (Medium Priority)
1. Add fraud indicators list
2. Add risk level guidelines
3. Add examples

### Phase 5: Add Examples (Low Priority)
1. Add complete flow examples
2. Add error case examples
3. Add decision examples

## Testing Plan

After implementing improvements:

1. **Test Scenario 1** (Matching Amount):
   - Verify all tools are called
   - Verify amount validation passes
   - Verify auto-approval

2. **Test Scenario 2** (Different Amount):
   - Verify mismatch detection
   - Verify contradiction flagging
   - Verify NEEDS_REVIEW decision

3. **Test Scenario 3** (No Images):
   - Verify image request
   - Verify appropriate decision

4. **Test Error Cases**:
   - Invalid PDF
   - Zero amount
   - No evidence

## Expected Improvements

After implementing these improvements:

1. **Tool Calling**: 100% of required tools called
2. **JSON Format**: 95%+ valid JSON responses
3. **Amount Validation**: Accurate mismatch detection
4. **Fraud Detection**: Better risk assessment
5. **Decision Quality**: More accurate decisions

## Metrics to Track

1. Tool calling completion rate
2. JSON parsing success rate
3. Amount validation accuracy
4. Fraud detection accuracy
5. Decision accuracy
