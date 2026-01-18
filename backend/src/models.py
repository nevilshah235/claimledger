"""Database models for ClaimLedger."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, Boolean, JSON
from sqlalchemy.orm import declarative_base, relationship

# Use String for UUID to support both SQLite and PostgreSQL
# SQLite doesn't have native UUID type
Base = declarative_base()


def generate_uuid():
    """Generate a UUID string."""
    return str(uuid4())


class Claim(Base):
    """Claim model - stores claim metadata and status."""

    __tablename__ = "claims"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claimant_address = Column(String(42), nullable=False)  # Ethereum address
    claim_amount = Column(Numeric(18, 2), nullable=False)  # USDC amount
    status = Column(
        String(20),
        nullable=False,
        default="SUBMITTED",
    )  # SUBMITTED, EVALUATING, APPROVED, SETTLED, REJECTED, AWAITING_DATA
    decision = Column(
        String(20),
        nullable=True,
    )  # AUTO_APPROVED, APPROVED_WITH_REVIEW, NEEDS_REVIEW, NEEDS_MORE_DATA, INSUFFICIENT_DATA, FRAUD_DETECTED, REJECTED
    confidence = Column(Float, nullable=True)  # 0.0-1.0
    approved_amount = Column(Numeric(18, 2), nullable=True)  # USDC amount
    processing_costs = Column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))  # Sum of x402 payments
    tx_hash = Column(String(66), nullable=True)  # Arc transaction hash
    auto_approved = Column(Boolean, default=False)  # Auto-approved by AI agent
    auto_settled = Column(Boolean, default=False)  # Auto-settled on blockchain
    comprehensive_summary = Column(Text, nullable=True)  # AI-generated summary
    review_reasons = Column(JSON, nullable=True)  # Reasons for manual review
    requested_data = Column(JSON, nullable=True)  # Types of additional data requested by agent
    human_review_required = Column(Boolean, default=False)  # Flag for human-in-the-loop
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    evidence = relationship("Evidence", back_populates="claim", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="claim", cascade="all, delete-orphan")
    x402_receipts = relationship("X402Receipt", back_populates="claim", cascade="all, delete-orphan")
    agent_results = relationship("AgentResult", back_populates="claim", cascade="all, delete-orphan")
    agent_logs = relationship("AgentLog", back_populates="claim", cascade="all, delete-orphan")


class Evidence(Base):
    """Evidence model - stores uploaded files (images/documents)."""

    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id"), nullable=False)
    file_type = Column(String(20), nullable=False)  # image, document
    file_path = Column(String(255), nullable=False)  # Local file path
    ipfs_hash = Column(String(64), nullable=True)  # Optional IPFS hash
    file_size = Column(Integer, nullable=True)  # File size in bytes
    mime_type = Column(String(100), nullable=True)  # MIME type
    analysis_metadata = Column(JSON, nullable=True)  # Store Gemini analysis results
    processing_status = Column(String(20), nullable=True, default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    claim = relationship("Claim", back_populates="evidence")


class Evaluation(Base):
    """Evaluation model - stores AI agent reasoning and decision."""

    __tablename__ = "evaluations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id"), nullable=False)
    reasoning = Column(Text, nullable=False)  # Agent reasoning trail
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    claim = relationship("Claim", back_populates="evaluations")


class X402Receipt(Base):
    """x402 receipt model - stores Gateway micropayment receipts."""

    __tablename__ = "x402_receipts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id"), nullable=False)
    verifier_type = Column(String(20), nullable=False)  # document, image, fraud
    amount = Column(Numeric(18, 2), nullable=False)  # USDC amount
    gateway_payment_id = Column(String(255), nullable=False)
    gateway_receipt = Column(String(255), nullable=False)  # Payment receipt token
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    claim = relationship("Claim", back_populates="x402_receipts")


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt hash
    role = Column(String(20), nullable=False)  # "claimant" or "insurer"
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    wallet = relationship("UserWallet", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserWallet(Base):
    """User-wallet mapping for Developer-Controlled Wallets."""

    __tablename__ = "user_wallets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)  # Our user ID
    wallet_address = Column(String(42), nullable=False)  # Ethereum address
    circle_wallet_id = Column(String(255), nullable=False)  # Circle wallet ID
    wallet_set_id = Column(String(255), nullable=True)  # Circle wallet set ID
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="wallet")


class AgentResult(Base):
    """Store results from each specialized agent."""
    
    __tablename__ = "agent_results"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id"), nullable=False)
    agent_type = Column(String(50), nullable=False)  # document, image, video, audio, fraud, reasoning
    result = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    claim = relationship("Claim", back_populates="agent_results")


class AgentLog(Base):
    """Store real-time activity logs from agents during evaluation."""
    
    __tablename__ = "agent_logs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id"), nullable=False)
    agent_type = Column(String(50), nullable=False)  # document, image, fraud, reasoning, orchestrator
    message = Column(Text, nullable=False)  # What the agent is doing/reasoning
    log_level = Column(String(20), nullable=False, default="INFO")  # INFO, DEBUG, WARNING, ERROR
    log_metadata = Column(JSON, nullable=True)  # Additional context (tool calls, file paths, etc.) - renamed from 'metadata' to avoid SQLAlchemy conflict
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    claim = relationship("Claim", back_populates="agent_logs")
