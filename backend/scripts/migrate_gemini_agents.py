"""
Database migration script for Gemini AI Agents integration.

Adds new columns and tables for:
- Auto-approval tracking (auto_approved, auto_settled, comprehensive_summary, review_reasons)
- Evidence metadata (file_size, mime_type, analysis_metadata, processing_status)
- Agent results tracking (agent_results table)

Run this script to update your database schema.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text, inspect
from src.database import engine, Base
from src.models import Claim, Evidence, AgentResult


def migrate_database():
    """Run database migration."""
    print("Starting database migration for Gemini AI Agents integration...")
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    # Check if claims table exists
    if "claims" not in existing_tables:
        print("Creating all tables from scratch...")
        Base.metadata.create_all(bind=engine)
        print("✓ All tables created")
        return
    
    # Get existing columns
    claims_columns = [col["name"] for col in inspector.get_columns("claims")]
    evidence_columns = [col["name"] for col in inspector.get_columns("evidence")]
    
    with engine.connect() as conn:
        # Add new columns to claims table
        print("\nUpdating claims table...")
        
        if "auto_approved" not in claims_columns:
            try:
                conn.execute(text("ALTER TABLE claims ADD COLUMN auto_approved BOOLEAN DEFAULT FALSE"))
                conn.commit()
                print("  ✓ Added auto_approved column")
            except Exception as e:
                print(f"  ⚠ Error adding auto_approved: {e}")
        
        if "auto_settled" not in claims_columns:
            try:
                conn.execute(text("ALTER TABLE claims ADD COLUMN auto_settled BOOLEAN DEFAULT FALSE"))
                conn.commit()
                print("  ✓ Added auto_settled column")
            except Exception as e:
                print(f"  ⚠ Error adding auto_settled: {e}")
        
        if "comprehensive_summary" not in claims_columns:
            try:
                # Use TEXT for SQLite, TEXT for PostgreSQL
                conn.execute(text("ALTER TABLE claims ADD COLUMN comprehensive_summary TEXT"))
                conn.commit()
                print("  ✓ Added comprehensive_summary column")
            except Exception as e:
                print(f"  ⚠ Error adding comprehensive_summary: {e}")
        
        if "review_reasons" not in claims_columns:
            try:
                # Use TEXT for SQLite (JSON stored as text), JSON for PostgreSQL
                db_url = str(engine.url)
                if "sqlite" in db_url.lower():
                    conn.execute(text("ALTER TABLE claims ADD COLUMN review_reasons TEXT"))
                else:
                    conn.execute(text("ALTER TABLE claims ADD COLUMN review_reasons JSON"))
                conn.commit()
                print("  ✓ Added review_reasons column")
            except Exception as e:
                print(f"  ⚠ Error adding review_reasons: {e}")
        
        # Add new columns to evidence table
        print("\nUpdating evidence table...")
        
        if "file_size" not in evidence_columns:
            try:
                conn.execute(text("ALTER TABLE evidence ADD COLUMN file_size INTEGER"))
                conn.commit()
                print("  ✓ Added file_size column")
            except Exception as e:
                print(f"  ⚠ Error adding file_size: {e}")
        
        if "mime_type" not in evidence_columns:
            try:
                conn.execute(text("ALTER TABLE evidence ADD COLUMN mime_type VARCHAR(100)"))
                conn.commit()
                print("  ✓ Added mime_type column")
            except Exception as e:
                print(f"  ⚠ Error adding mime_type: {e}")
        
        if "analysis_metadata" not in evidence_columns:
            try:
                db_url = str(engine.url)
                if "sqlite" in db_url.lower():
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN analysis_metadata TEXT"))
                else:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN analysis_metadata JSON"))
                conn.commit()
                print("  ✓ Added analysis_metadata column")
            except Exception as e:
                print(f"  ⚠ Error adding analysis_metadata: {e}")
        
        if "processing_status" not in evidence_columns:
            try:
                conn.execute(text("ALTER TABLE evidence ADD COLUMN processing_status VARCHAR(20) DEFAULT 'PENDING'"))
                conn.commit()
                print("  ✓ Added processing_status column")
            except Exception as e:
                print(f"  ⚠ Error adding processing_status: {e}")
        
        # Create agent_results table if it doesn't exist
        print("\nCreating agent_results table...")
        if "agent_results" not in existing_tables:
            try:
                # Create table using SQLAlchemy
                AgentResult.__table__.create(bind=engine, checkfirst=True)
                print("  ✓ Created agent_results table")
            except Exception as e:
                print(f"  ⚠ Error creating agent_results table: {e}")
        else:
            print("  ✓ agent_results table already exists")
    
    print("\n✓ Migration completed successfully!")


if __name__ == "__main__":
    migrate_database()
