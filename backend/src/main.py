"""
FastAPI application entry point.

ClaimLedger API - Agentic insurance claims with:
- Google Agents Framework for AI evaluation
- x402 micropayments via Circle Gateway
- USDC settlement on Arc blockchain
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db

# Import API routers
from .api.claims import router as claims_router
from .api.verifier import router as verifier_router
from .api.agent import router as agent_router
from .api.blockchain import router as blockchain_router
from .api.auth import router as auth_router


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

# CORS configuration - support both local dev and production Vercel URLs
cors_origins = [
    "http://localhost:3000",  # Next.js dev server
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://localhost:3000/",  # With trailing slash
]

# Add Vercel deployment URLs from environment if provided
vercel_url = os.getenv("VERCEL_URL")
vercel_preview_url = os.getenv("VERCEL_PREVIEW_URL")
if vercel_url:
    cors_origins.append(f"https://{vercel_url}")
if vercel_preview_url:
    cors_origins.append(f"https://{vercel_preview_url}")

# Allow custom frontend URL from environment
custom_frontend_url = os.getenv("FRONTEND_URL")
if custom_frontend_url:
    cors_origins.append(custom_frontend_url)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
