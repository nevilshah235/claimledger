# ClaimLedger

Autonomous, Multimodal Insurance Claims with Deterministic USDC Settlement on Arc

## Overview

ClaimLedger is an agentic insurance settlement platform where autonomous AI agents evaluate, verify, and settle insurance claims using multimodal evidence and onchain USDC payments.

**Tech Stack:**
- **Backend**: Python (FastAPI) with Google Agents Framework + Gemini 3 Pro
- **Frontend**: Next.js + TypeScript
- **Blockchain**: Arc (EVM-compatible L1) with USDC
- **Infrastructure**: Circle Wallets, Circle Gateway (x402), PostgreSQL

## Architecture

- **One Contract**: `ClaimEscrow.sol` - Escrow and settlement
- **One Agent**: Google Agents Framework with 4 explicit tools
- **Three x402 Verifiers**: Document, Image, Fraud (Gateway micropayments)
- **One Settlement**: USDC transfer on Arc

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL
- Rye (Python package manager)
- Foundry (for Solidity contracts)

### Setup

```bash
# Backend
cd backend
rye sync
rye run uvicorn src.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Contracts
cd contracts
forge build
forge test
```

## Development Workflow

- All features must include unit tests
- All changes via Pull Requests
- CI runs tests on every push
- Main branch must always be demoable

## License

MIT
