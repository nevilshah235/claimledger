# Contributing to ClaimLedger

This document outlines our development workflow and best practices.

## Git Workflow

We follow **GitHub Flow** - no direct commits to `main`.

```
main (protected)
  └── feat/feature-name
  └── fix/bug-description
  └── docs/documentation-update
  └── test/test-addition
```

### Branch Naming Convention

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feat/` | New features | `feat/circle-wallet-integration` |
| `fix/` | Bug fixes | `fix/uuid-handling` |
| `docs/` | Documentation | `docs/api-reference` |
| `test/` | Test additions | `test/agent-evaluation` |
| `refactor/` | Code refactoring | `refactor/database-models` |
| `chore/` | Maintenance tasks | `chore/update-dependencies` |

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `test`: Adding/updating tests
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

**Examples:**
```bash
feat(agent): add Gemini integration for claim evaluation
fix(api): resolve UUID handling for SQLite compatibility
docs(readme): update setup instructions
test(verifier): add x402 payment flow tests
```

## Development Commands

Use the provided `Makefile` for common tasks:

```bash
# Setup & Installation
make install          # Install all dependencies
make install-backend  # Install backend only
make install-frontend # Install frontend only

# Development
make dev              # Start both backend and frontend
make dev-backend      # Start backend only (port 8000)
make dev-frontend     # Start frontend only (port 3000)

# Testing
make test             # Run all tests
make test-backend     # Run backend tests
make test-frontend    # Run frontend tests
make test-contracts   # Run contract tests

# Code Quality
make lint             # Run linters
make format           # Format code
make check            # Run all checks (lint + test)

# Git Workflow
make branch name=feat/my-feature  # Create and checkout new branch
make pr                           # Create pull request
make sync                         # Sync with main branch

# Database
make db-reset         # Reset database
make db-migrate       # Run migrations

# Deployment
make deploy-contracts # Deploy contracts to testnet
```

## Pull Request Process

1. **Create feature branch:**
   ```bash
   make branch name=feat/my-feature
   ```

2. **Make changes and commit:**
   ```bash
   git add .
   git commit -m "feat(scope): description"
   ```

3. **Run checks before pushing:**
   ```bash
   make check
   ```

4. **Push and create PR:**
   ```bash
   git push -u origin feat/my-feature
   make pr
   ```

5. **PR Requirements:**
   - All tests pass
   - Code review approved
   - No merge conflicts
   - Conventional commit messages

## Testing Requirements

### Backend (pytest)
- Unit tests for all services
- Integration tests for API endpoints
- Minimum 80% coverage for new code

```bash
# Run with coverage
make test-backend-cov
```

### Frontend (jest/vitest)
- Component tests
- Integration tests
- E2E tests for critical flows

### Contracts (forge)
- Unit tests for all functions
- Fuzzing tests for edge cases

## Code Style

### Python (Backend)
- Formatter: `black`
- Linter: `ruff`
- Type hints required
- Docstrings for public functions

### TypeScript (Frontend)
- Formatter: `prettier`
- Linter: `eslint`
- Strict TypeScript mode

### Solidity (Contracts)
- Formatter: `forge fmt`
- NatSpec documentation required

## Directory Structure

```
claimledger/
├── .github/
│   └── workflows/      # CI/CD pipelines
├── backend/
│   ├── src/
│   │   ├── api/        # API endpoints
│   │   ├── agent/      # AI agent logic
│   │   ├── services/   # Business logic
│   │   └── models.py   # Database models
│   └── tests/          # Backend tests
├── frontend/
│   ├── app/            # Next.js pages
│   ├── components/     # React components
│   └── __tests__/      # Frontend tests
├── contracts/
│   ├── src/            # Solidity contracts
│   └── test/           # Contract tests
└── docs/               # Documentation
```

## Environment Setup

1. Copy environment templates:
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env.local
   ```

2. Fill in required values (see docs/CIRCLE_TESTNET_SETUP.md)

## Questions?

Open an issue or reach out to the maintainers.
