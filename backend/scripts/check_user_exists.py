#!/usr/bin/env python3
"""
Check if a user exists in the database.

Usage:
    python backend/scripts/check_user_exists.py <user_id>
    python backend/scripts/check_user_exists.py e69a8444-7dcf-4705-8586-ffb22052429e
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import SessionLocal
from src.models import User

def check_user(user_id: str):
    """Check if user exists in database."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            print(f"✅ User found:")
            print(f"   ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Role: {user.role}")
            return True
        else:
            print(f"❌ User not found: {user_id}")
            print(f"\nThis means:")
            print(f"  - Token is valid but user was deleted")
            print(f"  - Database was reset/recreated")
            print(f"  - User was created in different database")
            print(f"\nSolution: Log in again to get a fresh token")
            return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_user_exists.py <user_id>")
        sys.exit(1)
    
    user_id = sys.argv[1]
    exists = check_user(user_id)
    sys.exit(0 if exists else 1)
