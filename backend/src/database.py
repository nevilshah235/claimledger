"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base

# Database URL from environment
import os
from dotenv import load_dotenv

load_dotenv()

# Default to SQLite for quick testing (no PostgreSQL needed)
# For production, set DATABASE_URL to PostgreSQL connection string
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./claimledger.db")

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
