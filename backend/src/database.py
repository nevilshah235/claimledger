"""Database connection and session management."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.models import Base

# Database URL from environment
import os
from dotenv import load_dotenv

load_dotenv()

# Default to SQLite for quick testing (no PostgreSQL needed)
# For production, set DATABASE_URL to PostgreSQL connection string
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./claimledger.db")

# Connection timeout for cloud databases (seconds). Keep small so Cloud Run fails fast.
DB_CONNECT_TIMEOUT_SECONDS = int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "5"))

# Create engine
_connect_args = {}
if DATABASE_URL.startswith("postgresql"):
    # psycopg2/psycopg supports connect_timeout (seconds)
    _connect_args["connect_timeout"] = DB_CONNECT_TIMEOUT_SECONDS

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

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
    """Initialize database tables (creates tables if they don't exist)."""
    try:
        # For Cloud SQL, this will create tables in the existing database
        # The database instance itself is already created in Cloud SQL
        Base.metadata.create_all(bind=engine)
        db_info = DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL
        # Don't log full connection string for security
        if 'cloudsql' in DATABASE_URL.lower():
            print(f"✅ Database tables initialized (Cloud SQL)")
        else:
            print(f"✅ Database tables initialized (URL: {db_info})")
    except Exception as e:
        print(f"⚠️  Warning: Database table initialization failed: {e}")
        print("   The application will continue, but database operations may fail.")
        raise


def check_db_accessible() -> None:
    """
    Fail-fast connectivity check.

    - Opens a DB connection and runs `SELECT 1`.
    - Raises on failure so the app/container can fail fast in Cloud Run.
    """
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
