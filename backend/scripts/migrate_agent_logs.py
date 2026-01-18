"""
Database migration script for Agent Logs table.

Adds the agent_logs table for tracking real-time agent activity during claim evaluation.

Run this script to add the agent_logs table to your database schema.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text, inspect
from src.database import engine, Base
from src.models import AgentLog


def migrate_database():
    """Run database migration to add agent_logs table."""
    print("Starting database migration for Agent Logs table...")
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    # Check if claims table exists (to verify database is initialized)
    if "claims" not in existing_tables:
        print("Database not initialized. Creating all tables from scratch...")
        Base.metadata.create_all(bind=engine)
        print("✓ All tables created (including agent_logs)")
        return
    
    # Create agent_logs table if it doesn't exist
    print("\nCreating agent_logs table...")
    if "agent_logs" not in existing_tables:
        try:
            # Create table using SQLAlchemy
            AgentLog.__table__.create(bind=engine, checkfirst=True)
            print("  ✓ Created agent_logs table")
        except Exception as e:
            print(f"  ⚠ Error creating agent_logs table: {e}")
            # Try manual SQL creation as fallback
            try:
                db_url = str(engine.url)
                with engine.connect() as conn:
                    if "sqlite" in db_url.lower():
                        # SQLite syntax
                        conn.execute(text("""
                            CREATE TABLE agent_logs (
                                id VARCHAR(36) PRIMARY KEY,
                                claim_id VARCHAR(36) NOT NULL,
                                agent_type VARCHAR(50) NOT NULL,
                                message TEXT NOT NULL,
                                log_level VARCHAR(20) NOT NULL DEFAULT 'INFO',
                                log_metadata TEXT,
                                created_at DATETIME NOT NULL,
                                FOREIGN KEY (claim_id) REFERENCES claims(id)
                            )
                        """))
                        conn.commit()
                        print("  ✓ Created agent_logs table (SQLite)")
                    else:
                        # PostgreSQL syntax
                        conn.execute(text("""
                            CREATE TABLE agent_logs (
                                id VARCHAR(36) PRIMARY KEY,
                                claim_id VARCHAR(36) NOT NULL,
                                agent_type VARCHAR(50) NOT NULL,
                                message TEXT NOT NULL,
                                log_level VARCHAR(20) NOT NULL DEFAULT 'INFO',
                                log_metadata JSON,
                                created_at TIMESTAMP NOT NULL,
                                FOREIGN KEY (claim_id) REFERENCES claims(id)
                            )
                        """))
                        conn.commit()
                        print("  ✓ Created agent_logs table (PostgreSQL)")
            except Exception as e2:
                print(f"  ✗ Failed to create agent_logs table: {e2}")
                return
    else:
        print("  ✓ agent_logs table already exists")
    
    print("\n✓ Migration completed successfully!")


if __name__ == "__main__":
    migrate_database()
