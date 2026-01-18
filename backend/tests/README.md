# Gemini AI Agents Testing Guide

This guide covers the comprehensive testing strategy for the Gemini AI agents integration.

## Overview

The test suite includes:
- **Unit Tests**: Individual agent classes (DocumentAgent, ImageAgent, FraudAgent, ReasoningAgent)
- **Integration Tests**: MultiAgentOrchestrator coordination and agent interactions
- **API Tests**: `/agent/evaluate/{claim_id}` endpoint with full flow
- **E2E Tests**: Complete claim evaluation flow from submission to settlement
- **Error Handling Tests**: API timeouts, rate limits, network errors, malformed responses
- **Real API Tests**: Tests with actual Gemini API (conditional on API key)
- **Performance Tests**: Response times, parallel execution, concurrent evaluations

## Test Structure

```
backend/tests/
├── conftest.py                    # Test fixtures and configuration
├── test_agent.py                  # API endpoint tests
├── test_orchestrator.py          # Integration tests for orchestrator
├── test_e2e_agent_flow.py        # End-to-end tests
├── test_performance.py            # Performance tests
├── test_agents/
│   ├── __init__.py
│   ├── test_document_agent.py   # DocumentAgent unit tests
│   ├── test_image_agent.py       # ImageAgent unit tests
│   ├── test_fraud_agent.py       # FraudAgent unit tests
│   ├── test_reasoning_agent.py   # ReasoningAgent unit tests
│   ├── test_error_handling.py    # Error handling tests
│   └── test_real_api.py          # Real API tests
└── fixtures/                      # Test data files (PDFs, images)
```

## Running Tests

### Prerequisites

Install test dependencies:
```bash
cd backend
pip install -e ".[dev]"
```

Or with uv:
```bash
cd backend
uv sync --dev
```

### Basic Test Execution

**Run all tests (with mocks):**
```bash
pytest backend/tests/ -v
```

**Run unit tests only:**
```bash
pytest backend/tests/test_agents/ -v
```

**Run integration tests:**
```bash
pytest backend/tests/test_orchestrator.py -v
```

**Run API endpoint tests:**
```bash
pytest backend/tests/test_agent.py -v
```

**Run end-to-end tests:**
```bash
pytest backend/tests/test_e2e_agent_flow.py -v
```

### Running Tests with Real API

**Set API key:**
```bash
export GOOGLE_AI_API_KEY=your-api-key-here
```

**Run real API tests:**
```bash
pytest backend/tests/ -m real_api -v
```

**Run all tests including real API:**
```bash
pytest backend/tests/ -v  # Will skip real_api tests if key not set
```

### Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit`: Unit tests with mocked Gemini API
- `@pytest.mark.integration`: Integration tests with mocked Gemini API
- `@pytest.mark.real_api`: Tests that require real Gemini API (skip if no key)
- `@pytest.mark.slow`: Tests that take longer (real API calls, performance tests)

**Filter by marker:**
```bash
# Run only unit tests
pytest backend/tests/ -m unit -v

# Run only integration tests
pytest backend/tests/ -m integration -v

# Skip slow tests
pytest backend/tests/ -m "not slow" -v

# Run real API tests only
pytest backend/tests/ -m real_api -v
```

### Test Coverage

**Run with coverage:**
```bash
pytest backend/tests/ --cov=src/agent --cov-report=html
```

**View coverage report:**
```bash
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

## Test Fixtures

### Available Fixtures

**Agent Fixtures:**
- `mock_gemini_client`: Mocked Gemini API client
- `real_gemini_client`: Real Gemini client (conditional on API key)
- `gemini_api_key`: Fixture to get/skip based on API key availability

**File Fixtures:**
- `sample_pdf_file`: Temporary PDF file with invoice data
- `sample_receipt_image`: Temporary image file with receipt
- `sample_damage_photo`: Temporary damage photo
- `sample_fire_damage_photo`: Temporary fire damage photo
- `sample_water_damage_photo`: Temporary water damage photo

**Claim Fixtures:**
- `test_claim`: Basic test claim
- `test_claim_with_evidence`: Claim with attached evidence files
- `test_claim_high_confidence`: Claim that should auto-approve
- `test_claim_low_confidence`: Claim that needs review

**Service Fixtures:**
- `mock_blockchain_service`: Mocked blockchain service for settlement
- `mock_gateway_service`: Mocked gateway service for x402
- `mock_x402_client`: Mocked x402 client

### Using Fixtures

Fixtures are automatically available in test functions:

```python
def test_example(sample_pdf_file, mock_gemini_client):
    """Example test using fixtures."""
    agent = DocumentAgent(api_key="test-key")
    agent.client = mock_gemini_client
    
    documents = [{"file_path": sample_pdf_file}]
    result = await agent.analyze("claim-123", documents)
    
    assert result is not None
```

## Test Categories

### Unit Tests

**Location**: `backend/tests/test_agents/`

Tests individual agent classes:
- Initialization with/without API key
- Analysis with valid/invalid inputs
- Error handling (timeouts, rate limits, network errors)
- Mock fallback when API unavailable
- Data extraction and validation

**Example:**
```bash
pytest backend/tests/test_agents/test_document_agent.py -v
```

### Integration Tests

**Location**: `backend/tests/test_orchestrator.py`

Tests MultiAgentOrchestrator:
- Agent coordination
- Parallel execution
- Auto-approval logic (>= 95% confidence)
- Manual review logic (< 95% confidence)
- Auto-settlement flow
- Summary generation

**Example:**
```bash
pytest backend/tests/test_orchestrator.py -v
```

### API Tests

**Location**: `backend/tests/test_agent.py`

Tests `/agent/evaluate/{claim_id}` endpoint:
- Request/response validation
- Database record creation (AgentResult, Evaluation)
- Status transitions (SUBMITTED → EVALUATING → APPROVED/NEEDS_REVIEW)
- Auto-approved/auto-settled flags
- Summary and review reasons storage
- Transaction hash storage

**Example:**
```bash
pytest backend/tests/test_agent.py -v
```

### End-to-End Tests

**Location**: `backend/tests/test_e2e_agent_flow.py`

Tests complete claim evaluation flow:
- Claim creation → evaluation → approval/settlement
- Auto-approval flow
- Manual review flow
- Multiple claims sequential processing
- Claim re-evaluation

**Example:**
```bash
pytest backend/tests/test_e2e_agent_flow.py -v
```

### Error Handling Tests

**Location**: `backend/tests/test_agents/test_error_handling.py`

Tests error scenarios:
- API timeouts
- Rate limits
- Invalid API keys
- Quota exceeded
- Network errors
- Malformed responses
- Partial agent failures
- Graceful degradation

**Example:**
```bash
pytest backend/tests/test_agents/test_error_handling.py -v
```

### Real API Tests

**Location**: `backend/tests/test_agents/test_real_api.py`

Tests with actual Gemini API:
- Requires `GOOGLE_AI_API_KEY` environment variable
- Tests all agents with real API
- Integration test with all agents

**Example:**
```bash
export GOOGLE_AI_API_KEY=your-key
pytest backend/tests/test_agents/test_real_api.py -v
```

### Performance Tests

**Location**: `backend/tests/test_performance.py`

Tests performance characteristics:
- Agent response times
- Parallel execution performance
- API call efficiency
- Concurrent evaluations
- Timeout thresholds

**Example:**
```bash
pytest backend/tests/test_performance.py -v
```

## Environment Variables

### Required for Real API Tests

- `GOOGLE_AI_API_KEY`: Google Gemini API key (optional for mock tests)

### Optional Configuration

- `AGENT_MODEL`: Model to use (default: `gemini-2.0-flash`)
- `TEST_USE_REAL_API`: Flag to enable real API tests (default: false)
- `TEST_API_TIMEOUT`: Timeout for API calls in tests (default: 30s)

## CI/CD Integration

### GitHub Actions

Tests are configured to run in CI:

1. **PR Checks**: Run unit and integration tests with mocks (fast)
2. **Main Branch**: Run all tests including real API tests (with API key from secrets)
3. **Nightly Builds**: Run slow tests and performance tests

### Local CI Simulation

```bash
# Simulate PR checks (fast, no real API)
pytest backend/tests/ -m "not slow and not real_api" -v

# Simulate main branch (all tests)
export GOOGLE_AI_API_KEY=your-key
pytest backend/tests/ -v
```

## Troubleshooting

### Tests Fail with "GOOGLE_AI_API_KEY not set"

This is expected for real API tests. Either:
1. Set the environment variable: `export GOOGLE_AI_API_KEY=your-key`
2. Skip real API tests: `pytest backend/tests/ -m "not real_api" -v`

### Tests Fail with Import Errors

Install test dependencies:
```bash
cd backend
pip install -e ".[dev]"
```

### Tests Fail with Database Errors

Tests use in-memory SQLite. If you see database errors:
1. Check that `conftest.py` fixtures are working
2. Verify database models are imported correctly
3. Check for test isolation issues (tests modifying shared state)

### Performance Tests Fail

Performance tests have timing thresholds. If they fail:
1. Check system load (may be slow under load)
2. Adjust thresholds in test code if needed
3. Run performance tests separately: `pytest backend/tests/test_performance.py -v`

## Best Practices

1. **Use Mocks by Default**: Most tests should use mocked Gemini API for speed and reliability
2. **Mark Real API Tests**: Always mark real API tests with `@pytest.mark.real_api`
3. **Mark Slow Tests**: Mark slow tests with `@pytest.mark.slow`
4. **Test Isolation**: Each test should be independent and not rely on other tests
5. **Fixture Usage**: Use fixtures for reusable test data and mocks
6. **Error Scenarios**: Test both success and failure paths
7. **Edge Cases**: Test empty inputs, missing files, invalid data

## Test Coverage Goals

- **Unit Tests**: >90% coverage for agent classes
- **Integration Tests**: >80% coverage for orchestrator
- **API Tests**: All endpoints covered
- **E2E Tests**: Critical paths covered

## Contributing

When adding new tests:

1. Follow existing test structure and naming conventions
2. Use appropriate pytest markers
3. Add fixtures to `conftest.py` if reusable
4. Document any new test categories or patterns
5. Ensure tests pass with both mocks and real API (when applicable)

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Google Gemini API Documentation](https://ai.google.dev/docs)