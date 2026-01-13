# ClaimLedger Development Makefile
# Usage: make <target>

.PHONY: help install dev test lint format check clean branch pr sync

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Default target
help:
	@echo "$(BLUE)ClaimLedger Development Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Setup & Installation:$(NC)"
	@echo "  make install          - Install all dependencies"
	@echo "  make install-backend  - Install backend dependencies"
	@echo "  make install-frontend - Install frontend dependencies"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  make dev              - Start backend and frontend"
	@echo "  make dev-backend      - Start backend only (port 8000)"
	@echo "  make dev-frontend     - Start frontend only (port 3000)"
	@echo ""
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  make test             - Run all tests"
	@echo "  make test-backend     - Run backend tests"
	@echo "  make test-backend-cov - Run backend tests with coverage"
	@echo "  make test-frontend    - Run frontend tests"
	@echo "  make test-contracts   - Run contract tests"
	@echo "  make test-e2e         - Run E2E API tests"
	@echo ""
	@echo "$(GREEN)Code Quality:$(NC)"
	@echo "  make lint             - Run all linters"
	@echo "  make format           - Format all code"
	@echo "  make check            - Run lint + test (pre-commit)"
	@echo ""
	@echo "$(GREEN)Git Workflow:$(NC)"
	@echo "  make branch name=feat/x - Create and checkout branch"
	@echo "  make pr               - Push and create pull request"
	@echo "  make sync             - Sync current branch with main"
	@echo "  make status           - Show git and project status"
	@echo ""
	@echo "$(GREEN)Database:$(NC)"
	@echo "  make db-reset         - Reset SQLite database"
	@echo "  make db-shell         - Open database shell"
	@echo ""
	@echo "$(GREEN)Deployment:$(NC)"
	@echo "  make deploy-contracts - Deploy contracts to Arc testnet"

# =============================================================================
# INSTALLATION
# =============================================================================

install: install-backend install-frontend install-contracts
	@echo "$(GREEN)✓ All dependencies installed$(NC)"

install-backend:
	@echo "$(BLUE)Installing backend dependencies...$(NC)"
	cd backend && uv venv .venv && . .venv/bin/activate && uv pip install -e ".[dev]"
	@echo "$(GREEN)✓ Backend installed$(NC)"

install-frontend:
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	cd frontend && npm install
	@echo "$(GREEN)✓ Frontend installed$(NC)"

install-contracts:
	@echo "$(BLUE)Installing contract dependencies...$(NC)"
	cd contracts && forge install
	@echo "$(GREEN)✓ Contracts installed$(NC)"

# =============================================================================
# DEVELOPMENT SERVERS
# =============================================================================

dev:
	@echo "$(BLUE)Starting development servers...$(NC)"
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@make -j2 dev-backend dev-frontend

dev-backend:
	@echo "$(BLUE)Starting backend on port 8000...$(NC)"
	cd backend && . .venv/bin/activate && uvicorn src.main:app --reload --port 8000

dev-frontend:
	@echo "$(BLUE)Starting frontend on port 3000...$(NC)"
	cd frontend && npm run dev

# =============================================================================
# TESTING
# =============================================================================

test: test-backend test-contracts
	@echo "$(GREEN)✓ All tests passed$(NC)"

test-backend:
	@echo "$(BLUE)Running backend tests...$(NC)"
	cd backend && . .venv/bin/activate && pytest tests/ -v

test-backend-cov:
	@echo "$(BLUE)Running backend tests with coverage...$(NC)"
	cd backend && . .venv/bin/activate && pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-frontend:
	@echo "$(BLUE)Running frontend tests...$(NC)"
	cd frontend && npm test

test-contracts:
	@echo "$(BLUE)Running contract tests...$(NC)"
	cd contracts && forge test -v

test-e2e:
	@echo "$(BLUE)Running E2E API tests...$(NC)"
	@./scripts/test-e2e.sh

# =============================================================================
# CODE QUALITY
# =============================================================================

lint: lint-backend lint-contracts
	@echo "$(GREEN)✓ Linting complete$(NC)"

lint-backend:
	@echo "$(BLUE)Linting backend...$(NC)"
	cd backend && . .venv/bin/activate && ruff check src/ tests/

lint-contracts:
	@echo "$(BLUE)Linting contracts...$(NC)"
	cd contracts && forge fmt --check

format: format-backend format-contracts
	@echo "$(GREEN)✓ Formatting complete$(NC)"

format-backend:
	@echo "$(BLUE)Formatting backend...$(NC)"
	cd backend && . .venv/bin/activate && black src/ tests/ && ruff check --fix src/ tests/

format-contracts:
	@echo "$(BLUE)Formatting contracts...$(NC)"
	cd contracts && forge fmt

check: lint test
	@echo "$(GREEN)✓ All checks passed - ready to commit$(NC)"

# =============================================================================
# GIT WORKFLOW
# =============================================================================

# Ensure we're not on main before making changes
guard-main:
	@if [ "$$(git branch --show-current)" = "main" ]; then \
		echo "$(RED)Error: Cannot make changes directly on main branch$(NC)"; \
		echo "$(YELLOW)Create a feature branch first: make branch name=feat/your-feature$(NC)"; \
		exit 1; \
	fi

# Create and checkout a new branch
branch:
ifndef name
	@echo "$(RED)Error: Branch name required$(NC)"
	@echo "Usage: make branch name=feat/feature-name"
	@exit 1
endif
	@echo "$(BLUE)Creating branch: $(name)$(NC)"
	git checkout main
	git pull origin main
	git checkout -b $(name)
	@echo "$(GREEN)✓ Branch '$(name)' created and checked out$(NC)"
	@echo "$(YELLOW)Remember to push with: git push -u origin $(name)$(NC)"

# Push current branch and create PR
pr:
	@BRANCH=$$(git branch --show-current); \
	if [ "$$BRANCH" = "main" ]; then \
		echo "$(RED)Error: Cannot create PR from main branch$(NC)"; \
		exit 1; \
	fi; \
	echo "$(BLUE)Pushing branch and creating PR...$(NC)"; \
	git push -u origin $$BRANCH; \
	gh pr create --fill || echo "$(YELLOW)PR may already exist. Check: gh pr view$(NC)"

# Sync current branch with main
sync:
	@echo "$(BLUE)Syncing with main...$(NC)"
	git fetch origin main
	git rebase origin/main
	@echo "$(GREEN)✓ Branch synced with main$(NC)"

# Show project status
status:
	@echo "$(BLUE)=== Git Status ===$(NC)"
	@git status --short
	@echo ""
	@echo "$(BLUE)=== Current Branch ===$(NC)"
	@git branch --show-current
	@echo ""
	@echo "$(BLUE)=== Recent Commits ===$(NC)"
	@git log --oneline -5
	@echo ""
	@echo "$(BLUE)=== Backend Status ===$(NC)"
	@if [ -f backend/.venv/bin/activate ]; then echo "$(GREEN)✓ Virtual env exists$(NC)"; else echo "$(RED)✗ Virtual env missing$(NC)"; fi
	@if [ -f backend/claimledger.db ]; then echo "$(GREEN)✓ Database exists$(NC)"; else echo "$(YELLOW)○ No database$(NC)"; fi

# =============================================================================
# DATABASE
# =============================================================================

db-reset:
	@echo "$(BLUE)Resetting database...$(NC)"
	rm -f backend/claimledger.db
	@echo "$(GREEN)✓ Database reset$(NC)"

db-shell:
	@echo "$(BLUE)Opening database shell...$(NC)"
	sqlite3 backend/claimledger.db

# =============================================================================
# DEPLOYMENT
# =============================================================================

deploy-contracts:
	@echo "$(BLUE)Deploying contracts to Arc testnet...$(NC)"
	@if [ -z "$$DEPLOYER_PRIVATE_KEY" ]; then \
		echo "$(RED)Error: DEPLOYER_PRIVATE_KEY not set$(NC)"; \
		echo "Run: source contracts/setup-env.sh"; \
		exit 1; \
	fi
	cd contracts && forge script script/Deploy.s.sol:DeployScript --rpc-url arc_testnet --broadcast -vvvv

# =============================================================================
# CLEANUP
# =============================================================================

clean:
	@echo "$(BLUE)Cleaning up...$(NC)"
	rm -rf backend/.venv
	rm -rf backend/__pycache__
	rm -rf backend/.pytest_cache
	rm -rf backend/claimledger.db
	rm -rf frontend/node_modules
	rm -rf frontend/.next
	rm -rf contracts/out
	rm -rf contracts/cache
	@echo "$(GREEN)✓ Cleanup complete$(NC)"
