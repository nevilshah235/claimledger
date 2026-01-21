"""
FastAPI application entry point.

ClaimLedger API - Agentic insurance claims with:
- Google Agents Framework for AI evaluation
- x402 micropayments via Circle Gateway
- USDC settlement on Arc blockchain
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import check_db_accessible, init_db

# Import API routers
from .api.claims import router as claims_router
from .api.verifier import router as verifier_router
from .api.agent import router as agent_router
from .api.blockchain import router as blockchain_router
from .api.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    print("🚀 Starting ClaimLedger API...")

    # Fail-fast: verify Cloud SQL / DB is reachable.
    # If this fails, the container should crash so Cloud Run reports a clear startup failure.
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, check_db_accessible)
        print("✅ Database is reachable")
    except Exception as e:
        print(f"❌ Database is NOT reachable: {type(e).__name__}: {e}")
        raise

    # Initialize DB schema after connectivity is confirmed.
    async def init_db_async():
        try:
            # Run in thread pool to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, init_db)
        except Exception as e:
            print(f"❌ Database schema initialization failed: {type(e).__name__}: {e}")
            raise
    
    await init_db_async()
    
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
        "https://claimledger.vercel.app",
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    # Allow Vercel previews and Cloud Run default domains.
    # Origin never includes a trailing slash, so regex matches exact host origins.
    allow_origin_regex=r"^https://.*\.(vercel\.app|a\.run\.app)$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include API routers
app.include_router(claims_router)
app.include_router(verifier_router)
app.include_router(agent_router)
app.include_router(blockchain_router)
app.include_router(auth_router)


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
            "blockchain": "/blockchain",
            "auth": "/auth"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
