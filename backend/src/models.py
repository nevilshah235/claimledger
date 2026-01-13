"""Database models for ClaimLedger."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Claim(Base):
    """Claim model - stores claim metadata and status."""

    __tablename__ = "claims"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    claimant_address = Column(String(42), nullable=False)  # Ethereum address
    claim_amount = Column(Numeric(18, 2), nullable=False)  # USDC amount
    status = Column(
        String(20),
        nullable=False,
        default="SUBMITTED",
    )  # SUBMITTED, EVALUATING, APPROVED, SETTLED, REJECTED
    decision = Column(
        String(20),
        nullable=True,
    )  # APPROVED, NEEDS_REVIEW, REJECTED
    confidence = Column(Float, nullable=True)  # 0.0-1.0
    approved_amount = Column(Numeric(18, 2), nullable=True)  # USDC amount
    processing_costs = Column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))  # Sum of x402 payments
    tx_hash = Column(String(66), nullable=True)  # Arc transaction hash
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    evidence = relationship("Evidence", back_populates="claim", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="claim", cascade="all, delete-orphan")
    x402_receipts = relationship("X402Receipt", back_populates="claim", cascade="all, delete-orphan")


class Evidence(Base):
    """Evidence model - stores uploaded files (images/documents)."""

    __tablename__ = "evidence"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    claim_id = Column(PGUUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    file_type = Column(String(20), nullable=False)  # image, document
    file_path = Column(String(255), nullable=False)  # Local file path
    ipfs_hash = Column(String(64), nullable=True)  # Optional IPFS hash
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    claim = relationship("Claim", back_populates="evidence")


class Evaluation(Base):
    """Evaluation model - stores AI agent reasoning and decision."""

    __tablename__ = "evaluations"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    claim_id = Column(PGUUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    reasoning = Column(Text, nullable=False)  # Agent reasoning trail
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    claim = relationship("Claim", back_populates="evaluations")


class X402Receipt(Base):
    """x402 receipt model - stores Gateway micropayment receipts."""

    __tablename__ = "x402_receipts"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    claim_id = Column(PGUUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    verifier_type = Column(String(20), nullable=False)  # document, image, fraud
    amount = Column(Numeric(18, 2), nullable=False)  # USDC amount
    gateway_payment_id = Column(String(255), nullable=False)
    gateway_receipt = Column(String(255), nullable=False)  # Payment receipt token
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    claim = relationship("Claim", back_populates="x402_receipts")
