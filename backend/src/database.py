"""Database connection and session management."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.models import Base

# Database URL from environment
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory (where this file is located)
# Go up from src/database.py to backend/
backend_dir = Path(__file__).parent.parent.parent
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)

# Default to SQLite for quick testing (no PostgreSQL needed)
# For production, set DATABASE_URL to PostgreSQL connection string
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./claimledger.db")

# Connection timeout for cloud databases (seconds).
# For Cloud SQL, the socket may take a few seconds to be ready.
DB_CONNECT_TIMEOUT_SECONDS = int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "10"))

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

        # Lightweight schema patching (for environments without migrations).
        # Adds columns newer code expects when running against an older DB.
        with engine.connect() as conn:
            dialect = conn.dialect.name

            if dialect == "sqlite":
                cols = [row[1] for row in conn.execute(text("PRAGMA table_info(claims)")).fetchall()]
                if "description" not in cols:
                    conn.execute(text("ALTER TABLE claims ADD COLUMN description TEXT"))
                if "decision_overridden" not in cols:
                    conn.execute(text("ALTER TABLE claims ADD COLUMN decision_overridden INTEGER DEFAULT 0"))
                if "contradictions" not in cols:
                    conn.execute(text("ALTER TABLE claims ADD COLUMN contradictions TEXT"))
                if "auto_approved" not in cols:
                    conn.execute(text("ALTER TABLE claims ADD COLUMN auto_approved INTEGER DEFAULT 0"))
                if "auto_settled" not in cols:
                    conn.execute(text("ALTER TABLE claims ADD COLUMN auto_settled INTEGER DEFAULT 0"))
                if "comprehensive_summary" not in cols:
                    conn.execute(text("ALTER TABLE claims ADD COLUMN comprehensive_summary TEXT"))
                if "review_reasons" not in cols:
                    conn.execute(text("ALTER TABLE claims ADD COLUMN review_reasons TEXT"))
                if "requested_data" not in cols:
                    conn.execute(text("ALTER TABLE claims ADD COLUMN requested_data TEXT"))
                if "human_review_required" not in cols:
                    conn.execute(text("ALTER TABLE claims ADD COLUMN human_review_required INTEGER DEFAULT 0"))
            elif dialect == "postgresql":
                def _col_exists(t: str, c: str) -> bool:
                    return conn.execute(
                        text(
                            "SELECT 1 FROM information_schema.columns "
                            "WHERE table_name = :t AND column_name = :c"
                        ),
                        {"t": t, "c": c},
                    ).first() is not None

                if not _col_exists("claims", "description"):
                    conn.execute(text("ALTER TABLE claims ADD COLUMN description TEXT"))
                if not _col_exists("claims", "decision_overridden"):
                    conn.execute(text("ALTER TABLE claims ADD COLUMN decision_overridden BOOLEAN DEFAULT FALSE"))
                if not _col_exists("claims", "contradictions"):
                    conn.execute(text("ALTER TABLE claims ADD COLUMN contradictions JSON"))
                if not _col_exists("claims", "auto_approved"):
                    conn.execute(text("ALTER TABLE claims ADD COLUMN auto_approved BOOLEAN DEFAULT FALSE"))
                if not _col_exists("claims", "auto_settled"):
                    conn.execute(text("ALTER TABLE claims ADD COLUMN auto_settled BOOLEAN DEFAULT FALSE"))
                if not _col_exists("claims", "comprehensive_summary"):
                    conn.execute(text("ALTER TABLE claims ADD COLUMN comprehensive_summary TEXT"))
                if not _col_exists("claims", "review_reasons"):
                    conn.execute(text("ALTER TABLE claims ADD COLUMN review_reasons JSON"))
                if not _col_exists("claims", "requested_data"):
                    conn.execute(text("ALTER TABLE claims ADD COLUMN requested_data JSON"))
                if not _col_exists("claims", "human_review_required"):
                    conn.execute(text("ALTER TABLE claims ADD COLUMN human_review_required BOOLEAN DEFAULT FALSE"))

            conn.commit()

        db_info = DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL
        # Don't log full connection string for security
        if 'cloudsql' in DATABASE_URL.lower():
            print(f"✅ Database tables initialized (Cloud SQL)")
        else:
            print(f"✅ Database tables initialized (URL: {db_info})")
        
        # Note: Users should be created via frontend registration, not seeded automatically
    except Exception as e:
        print(f"⚠️  Warning: Database table initialization failed: {e}")
        print("   The application will continue, but database operations may fail.")
        raise


def check_db_accessible() -> None:
    """
    Fail-fast connectivity check with retry logic.

    - Opens a DB connection and runs `SELECT 1`.
    - Retries with exponential backoff for Cloud SQL (socket may not be ready immediately).
    - Raises on failure so the app/container can fail fast in Cloud Run.
    """
    import time
    
    max_retries = 10
    retry_delay = 1  # Start with 1 second
    
    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return  # Success!
        except Exception as e:
            if attempt == max_retries - 1:
                # Last attempt failed, raise the error
                raise
            # Check if it's a connection error (socket not ready)
            error_str = str(e).lower()
            if "connection refused" in error_str or "socket" in error_str:
                print(f"⏳ Waiting for database socket (attempt {attempt + 1}/{max_retries})...")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 5)  # Exponential backoff, max 5s
            else:
                # Different error, don't retry
                raise
