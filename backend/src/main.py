"""
FastAPI application entry point.

ClaimLedger API - Agentic insurance claims with:
- Google Agents Framework for AI evaluation
- x402 micropayments via Circle Gateway
- USDC settlement on Arc blockchain
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db

# Import API routers
from .api.claims import router as claims_router
from .api.verifier import router as verifier_router
from .api.agent import router as agent_router
from .api.blockchain import router as blockchain_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup: Create database tables
    print("🚀 Starting ClaimLedger API...")
    init_db()
    print("✅ Database tables created/verified")
    yield
    # Shutdown
    print("👋 Shutting down ClaimLedger API...")


app = FastAPI(
    title="ClaimLedger API",
    lifespan=lifespan,
    description="""
    Agentic insurance claims platform with:
    - Multimodal claim submission
    - AI agent evaluation (Google Agents Framework + Gemini)
    - x402 micropayments via Circle Gateway
    - USDC settlement on Arc blockchain
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(claims_router)
app.include_router(verifier_router)
app.include_router(agent_router)
app.include_router(blockchain_router)


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "service": "ClaimLedger API",
        "version": "0.1.0",
        "status": "ok",
        "docs": "/docs",
        "endpoints": {
            "claims": "/claims",
            "verifier": "/verifier",
            "agent": "/agent",
            "blockchain": "/blockchain"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
