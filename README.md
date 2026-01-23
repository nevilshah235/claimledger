# ClaimLedger

![UClaim Logo](frontend/public/uclaim-logo-transparent.png)

**Autonomous, multimodal insurance claims with deterministic USDC settlement on Arc**

An agentic insurance platform that combines **Google ADK** (Agent Development Kit) + **Gemini** for intelligent claim evaluation, **x402 micropayments** via Circle Gateway, and **Arc blockchain** with native USDC for transparent settlements. Deployed on **Vercel** (frontend) and **Google Cloud Run** (backend). Built to showcase AI agents, programmable payments, and on-chain settlement in a single flow.

---

## Why ClaimLedger?

| What | How |
|------|-----|
| **AI that actually decides** | ADK orchestrator with a 4-layer tool pipeline: extract → estimate → validate → verify. Six decision types from AUTO_APPROVED to FRAUD_DETECTED. |
| **Pay only for verification** | Free extraction and cost checks; x402 pays only for document ($0.05), image ($0.10), and fraud ($0.05) verification (~$0.20/claim). |
| **Deterministic settlement** | Fail-closed: no funds move unless confidence ≥ 85%. Auto-settle at 95% when fraud risk &lt; 30%. |
| **Real USDC, no backend keys** | Insurer signs in-browser with Circle User-Controlled wallets; ClaimEscrow on Arc. No `INSURER_WALLET_PRIVATE_KEY`. |

---

## Features

### AI agent (Google ADK + Gemini)

- **Google ADK** (Agent Development Kit) for orchestration and autonomous tool-calling with Gemini.
- **Orchestrator** with 9 tools: `extract_document_data`, `extract_image_data`, `estimate_repair_cost`, `cross_check_amounts`, `validate_claim_data`, `verify_document`, `verify_image`, `verify_fraud`, `approve_claim`.
- **4-layer pipeline**: (1) Extract (free), (2) Cost estimation (free), (3) Validation (free), (4) Verification (x402).
- **Decisions**: `AUTO_APPROVED`, `APPROVED_WITH_REVIEW`, `NEEDS_REVIEW`, `NEEDS_MORE_DATA`, `INSUFFICIENT_DATA`, `FRAUD_DETECTED`.
- **Auto-approve / auto-settle** when confidence ≥ 95%, no contradictions, fraud risk &lt; 30%.

### x402 + Circle

- **Micropayments** for verification only: document $0.05, image $0.10, fraud $0.05 (~$0.20/claim).
- **Insurer wallet** pays; balance and fee tracking via `GET /admin/fees`.
- **Note:** The `/verifier` (x402) endpoints and flow exist in code but are **not currently used** in the active evaluation path.

### Arc + ClaimEscrow

- **User-controlled wallets** (Circle) for insurer and claimant; settlement via `ClaimEscrow` on Arc. Target: 3-step user-signed flow (`approve` → `depositEscrow` → `approveClaim`) — see [REAL_USDC_SETTLEMENT](docs/REAL_USDC_SETTLEMENT.md).
- **ClaimEscrow** on Arc: escrow and release to claimant; tx hashes and block explorer links.

### Frontend (Next.js)

- **Landing**: hero, stats, feature strip (AI, Circle, Arc), scroll-reveal, role CTAs.
- **Claimant**: ClaimForm, ClaimStatus, VerificationSteps, ExtractedInfoSummary, DataRequestCard, EvaluationProgress, WalletDisplay.
- **Insurer**: FinanceKpiStrip, InsurerClaimReview, SettlementCard, AgentResultsBreakdown, AdminFeeTracker, AutoSettleWalletCard, TxValidationStatus, EnableSettlementsModal.
- **ChatAssistant**: implemented but **not in use** (commented out in UI).
- **Auth**: JWT, email/password, roles (claimant/insurer). Optional `ADMIN_WALLET_ADDRESS` for admin auto-login.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend  │  Next.js, TypeScript, Tailwind, Circle Wallets SDK  │
│  Landing │ Claimant │ Insurer │ EnableSettlements              │
└─────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────┐
│  Backend  │  FastAPI, SQLAlchemy, JWT                            │
│  /claims │ /agent/evaluate, status, results, logs                │
│  /blockchain/settle │ /admin/fees, /admin/status                 │
│  /auth (register, login, me, wallet) │ /verifier (x402, not in use) │
└─────────────────────────────────────────────────────────────────┘
        │                    │                        │
┌───────┴───────┐  ┌─────────┴─────────┐  ┌──────────┴──────────┐
│  ADK Orchestrator + 4-layer tools    │  │  Circle Gateway     │  │  Arc + ClaimEscrow   │
│  extract → estimate → validate       │  │  x402 micropayments │  │  User-signed settle  │
│  → verify_document, verify_image,    │  │  Balance / fees     │  │  USDC, no backend PK │
│    verify_fraud, approve_claim       │  │                     │  │                      │
└───────────────┘  └──────────────────┘  └─────────────────────┘
```

- **One contract**: `ClaimEscrow.sol` (deposit, approveClaim, escrow).
- **One orchestrator**: ADK `LlmAgent` with 9 tools (4 free + 3 paid + approve_claim).
- **Three x402 verifiers**: document, image, fraud (implemented; not in use in current flow).
- **Settlement**: 3-step challenge (approve USDC, depositEscrow, approveClaim) via Circle User-Controlled + Arc.

See [docs/HLD.md](docs/HLD.md) and [docs/LLD.md](docs/LLD.md).

---

## Tech stack

| Layer | Tech |
|-------|------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy, uv, JWT (python-jose) |
| **AI** | **Google ADK** (Agent Development Kit), google-genai, Gemini 2.0 Flash |
| **Frontend** | Next.js 14, TypeScript, Tailwind, React Query, Circle Wallets SDK |
| **Blockchain** | Solidity 0.8.20, Foundry, Arc testnet, USDC |
| **Deployment** | **Vercel** (frontend), **Google Cloud Run** (backend); optional Cloud SQL for PostgreSQL |
| **External** | Google Gemini, Circle Gateway (x402), Circle Wallets (user-controlled) |

---

## Deployment

- **Frontend:** **Vercel** — Next.js app with serverless functions, global CDN, and automatic previews.
- **Backend:** **Google Cloud Run** — FastAPI container; optional **Cloud SQL** (PostgreSQL) for production.

See [docs/VERCEL_CLOUD_RUN_DEPLOYMENT.md](docs/VERCEL_CLOUD_RUN_DEPLOYMENT.md) for step-by-step setup.

---

## Quick start

### 1. Backend

```bash
cd backend
cp .env.example .env   # set DATABASE_URL, JWT_SECRET_KEY, GOOGLE_AI_API_KEY or GOOGLE_API_KEY;
                      # optional: CIRCLE_*, ARC_*, USDC_ADDRESS, CLAIM_ESCROW_ADDRESS
uv sync
uv run uvicorn src.main:app --reload
# → http://localhost:8000
```

### 2. Frontend

```bash
cd frontend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm install && npm run dev
# → http://localhost:3000
```

### 3. Contracts (optional)

```bash
cd contracts
forge build && forge test
```

**Testnet mode**: No Circle credentials → mock wallets; full off-chain flow works. For real USDC settlement, configure Circle (Wallets + Gateway) and Arc env vars. See [docs/ENVIRONMENT_VARIABLES.md](docs/ENVIRONMENT_VARIABLES.md), [docs/TESTNET_MODE.md](docs/TESTNET_MODE.md), [docs/REAL_USDC_SETTLEMENT.md](docs/REAL_USDC_SETTLEMENT.md).

---

## Demo flow

1. **Claimant**: Register → Submit claim (amount, evidence) → Track status (EvaluationProgress, ExtractedInfoSummary, DataRequestCard).
2. **Insurer**: Login → Trigger evaluation (x402 ~$0.20) → Review AgentResultsBreakdown, review_reasons, requested_data.
3. **Settlement**: Enable settlements (Circle) if needed → Approve → depositEscrow → approveClaim (TxValidationStatus, tx_hash).
4. **Auto-path**: If confidence ≥ 95% and fraud &lt; 30%, agent can auto-approve and (when wired) auto-settle.

---

## Project structure

```
├── backend/src/
│   ├── api/          claims, agent, verifier, blockchain, auth, admin
│   ├── agent/        agent.py, tools*.py, adk_tools, adk_schemas, adk_agents/, adk_runtime
│   ├── services/     x402_client, gateway, blockchain, circle_wallets
│   ├── models.py, database.py, main.py
├── frontend/app/
│   ├── page.tsx      landing
│   ├── claimant/     claimant dashboard
│   ├── insurer/      insurer dashboard
│   ├── components/   ClaimForm, ClaimStatus, InsurerClaimReview, SettlementCard,
│   │                 AdminFeeTracker, AgentResultsBreakdown, AutoSettleWalletCard,
│   │                 EnableSettlementsModal, TxValidationStatus (ChatAssistant: not in use)
├── contracts/src/
│   └── ClaimEscrow.sol
└── docs/             HLD, LLD, ENVIRONMENT_VARIABLES, TESTNET_MODE, REAL_USDC_SETTLEMENT, …
```

---

## API (high level)

| Area | Endpoints |
|------|-----------|
| **Claims** | `POST /claims`, `GET /claims`, `GET /claims/{id}` |
| **Agent** | `POST /agent/evaluate/{id}`, `GET /agent/status/{id}`, `GET /agent/results/{id}`, `GET /agent/logs/{id}` *(POST /agent/chat and /verifier: not in use)* |
| **Blockchain** | `POST /blockchain/settle/{id}` (see [REAL_USDC_SETTLEMENT](docs/REAL_USDC_SETTLEMENT.md) for user-signed challenge/complete flow) |
| **Admin** | `GET /admin/fees`, `GET /admin/status` |
| **Auth** | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `GET /auth/wallet` |

OpenAPI: `http://localhost:8000/docs` when the backend is running.

---

## Docs

- [High-Level Design (HLD)](docs/HLD.md)
- [Low-Level Design (LLD)](docs/LLD.md)
- [Vercel + Google Cloud Run deployment](docs/VERCEL_CLOUD_RUN_DEPLOYMENT.md)
- [Environment variables](docs/ENVIRONMENT_VARIABLES.md)
- [Testnet mode](docs/TESTNET_MODE.md)
- [Real USDC settlement](docs/REAL_USDC_SETTLEMENT.md)
- [Quick start testing](docs/QUICK_START_TESTING.md)
- [Circle Wallets: Developer- vs User-Controlled (automated vs. manual validation)](docs/CIRCLE_WALLETS_INTEGRATION_TYPES.md)

---

## License

MIT
