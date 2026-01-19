# Commit Recommendations for Remaining Files

## ✅ **MUST COMMIT NOW** (Critical - Code Will Break Without These)

### 1. `backend/src/agent/adk_schemas.py` ⚠️ **CRITICAL**
**Why**: Used by all ADK agents (document, fraud, reasoning, orchestrator, image)  
**Impact**: Code will fail without this file  
**Action**: Commit immediately

```bash
git add backend/src/agent/adk_schemas.py
git commit -m "feat(adk): add ADK agent output schemas

- Add ORCHESTRATOR_SCHEMA for orchestrator agent validation
- Add DOCUMENT_SCHEMA for document agent validation  
- Add FRAUD_SCHEMA for fraud agent validation
- Add REASONING_SCHEMA for reasoning agent validation
- Add IMAGE_SCHEMA for image agent validation

Required by all ADK agents for structured output validation"
```

---

## ✅ **SHOULD COMMIT** (Needed for Testing & Utilities)

### 2. `backend/tests/test_orchestrator.py`
**Why**: Integration tests for ADKOrchestrator wrapper (different from plan improvements tests)  
**Action**: Commit

```bash
git add backend/tests/test_orchestrator.py
git commit -m "test(orchestrator): add ADKOrchestrator integration tests

- Test orchestrator initialization and singleton pattern
- Test agent coordination and evaluation flow
- Complements test_orchestrator_plan_improvements.py"
```

### 3. `frontend/__tests__/e2e/agent-flow.test.tsx`
**Why**: Frontend E2E tests for agent flow  
**Action**: Commit

```bash
git add frontend/__tests__/e2e/
git commit -m "test(frontend): add E2E tests for agent flow

- Add agent-flow.test.tsx for end-to-end testing
- Tests complete agent evaluation workflow in frontend"
```

### 4-5. Migration Scripts
**Why**: Production database migration utilities  
**Action**: Commit

```bash
git add backend/scripts/migrate_agent_logs.py backend/scripts/migrate_gemini_agents.py
git commit -m "chore(scripts): add database migration scripts

- Add migrate_agent_logs.py for agent_logs table migration
- Add migrate_gemini_agents.py for Gemini AI Agents schema migration
- Production utilities for database schema updates"
```

### 6-8. Test Utilities
**Why**: Development and testing utilities  
**Action**: Commit

```bash
git add backend/scripts/test_pdf_extraction.py scripts/test-e2e-agentic.sh backend/test_gateway_simple.py backend/src/agent/adk_agents/test_agent.py
git commit -m "chore(scripts): add development and test utilities

- Add test_pdf_extraction.py for PDF extraction testing
- Add test-e2e-agentic.sh for E2E agentic flow testing  
- Add test_gateway_simple.py for isolated gateway testing
- Add test_agent.py for ADK setup verification

Useful utilities for development and CI/CD"
```

---

## ⚠️ **REVIEW & DECIDE** (Legacy Code - Likely Obsolete)

### 9. `backend/src/agent/orchestrator.py` (Legacy)
**Status**: ❌ **NOT USED** - No imports found in API or main.py  
**Purpose**: Old MultiAgentOrchestrator implementation  
**Replacement**: `backend/src/agent/adk_agents/orchestrator.py` (new ADK version)

**Recommendation**: **DELETE** (not used, replaced by ADK version)

```bash
# Verify it's not used first
grep -r "from.*\.orchestrator import\|MultiAgentOrchestrator" backend/src/api/ backend/src/main.py

# If not found, delete:
git rm backend/src/agent/orchestrator.py
git commit -m "chore: remove legacy orchestrator

- Remove old MultiAgentOrchestrator implementation
- Replaced by ADKOrchestrator in adk_agents/orchestrator.py
- Not used anywhere in codebase"
```

### 10. `backend/src/agent/agents/` (Legacy)
**Status**: ❌ **ONLY USED BY LEGACY ORCHESTRATOR**  
**Purpose**: Old agent implementations (DocumentAgent, ImageAgent, etc.)  
**Replacement**: `backend/src/agent/adk_agents/` (new ADK implementations)

**Recommendation**: **DELETE** (only used by legacy orchestrator, which should be deleted)

```bash
# After deleting legacy orchestrator, delete agents:
git rm -r backend/src/agent/agents/
git commit -m "chore: remove legacy agent implementations

- Remove old agents/ directory (DocumentAgent, ImageAgent, etc.)
- Replaced by ADK implementations in adk_agents/
- Only used by legacy orchestrator which has been removed"
```

---

## 📋 **Quick Commit Script**

Run this to commit all recommended files:

```bash
# Critical - adk_schemas.py
git add backend/src/agent/adk_schemas.py
git commit -m "feat(adk): add ADK agent output schemas

Required by all ADK agents for structured output validation"

# Tests
git add backend/tests/test_orchestrator.py frontend/__tests__/e2e/
git commit -m "test: add orchestrator integration tests and frontend E2E tests"

# Migration scripts
git add backend/scripts/migrate_agent_logs.py backend/scripts/migrate_gemini_agents.py
git commit -m "chore(scripts): add database migration scripts"

# Test utilities
git add backend/scripts/test_pdf_extraction.py scripts/test-e2e-agentic.sh backend/test_gateway_simple.py backend/src/agent/adk_agents/test_agent.py
git commit -m "chore(scripts): add development and test utilities"

# Optional: Delete legacy code
git rm backend/src/agent/orchestrator.py backend/src/agent/agents/
git commit -m "chore: remove legacy orchestrator and agents

Replaced by ADK implementations"
```

---

## 🎯 **Summary**

**Must Commit**: 1 file (adk_schemas.py)  
**Should Commit**: 7 files/directories (tests, migrations, utilities)  
**Review & Delete**: 2 files/directories (legacy code)

**Total**: 8 files/directories to commit, 2 to review/delete
