#!/usr/bin/env python3
"""
Test Cloud SQL PostgreSQL connection from local machine.
This script can be run directly or from a Docker container.
"""

import os
import sys
from urllib.parse import quote_plus

# Database credentials from .env.production.yaml
DB_USER = "claimledger-user"
DB_PASSWORD = "vD8!qN2#Zp7@Lm5$Tx9^aR3*Hc6%Yw1&"
DB_NAME = "claimledger"
PUBLIC_IP = "34.31.234.152"  # From gcloud sql instances describe

def test_connection():
    """Test PostgreSQL connection."""
    try:
        import psycopg2
    except ImportError:
        print("❌ psycopg2 not installed. Install with: pip install psycopg2-binary")
        sys.exit(1)
    
    # Test with public IP
    print(f"🔍 Testing connection to {PUBLIC_IP}...")
    print(f"   Database: {DB_NAME}")
    print(f"   User: {DB_USER}")
    
    try:
        conn = psycopg2.connect(
            host=PUBLIC_IP,
            port=5432,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=10
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Connection successful!")
        print(f"   PostgreSQL version: {version}")
        
        # Test a simple query
        cursor.execute("SELECT current_database(), current_user;")
        db_info = cursor.fetchone()
        print(f"   Current database: {db_info[0]}")
        print(f"   Current user: {db_info[1]}")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Verify Cloud SQL instance is running:")
        print("      bash scripts/gcloud-deployment.sh status cloudsql")
        print("   2. Check if your IP is authorized:")
        print("      gcloud sql instances describe claimledger-db --format='value(settings.ipConfiguration.authorizedNetworks)'")
        print("   3. Authorize your IP:")
        print("      gcloud sql instances patch claimledger-db --authorized-networks=YOUR_IP/32")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
