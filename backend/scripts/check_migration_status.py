#!/usr/bin/env python3
"""
Diagnostic script to check migration status and database connection.

This helps debug why migrations might not be persisting to Supabase.
"""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402


def check_migration_status() -> None:
    """Check current migration status and database connection."""
    print("=" * 60)
    print("Migration Status Diagnostic")
    print("=" * 60)

    # 1. Check environment
    print(f"\n1. Environment:")
    print(f"   PROFILE: {settings.PROFILE}")
    print(f"   DATABASE_URL: {settings.database_url[:50]}..." if len(settings.database_url) > 50 else f"   DATABASE_URL: {settings.database_url}")
    print(f"   STORAGE_TYPE: {settings.STORAGE_TYPE}")

    # 2. Check database connection
    print(f"\n2. Database Connection:")
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT version()"))
        db_version = result.scalar()
        print(f"   ✅ Connected to database")
        print(f"   Database: {db_version.split(',')[0] if db_version else 'Unknown'}")

        # 3. Check alembic_version table
        print(f"\n3. Alembic Version Table:")
        try:
            result = db.execute(text("SELECT version_num FROM alembic_version"))
            current_version = result.scalar()
            print(f"   Current version: {current_version}")
        except Exception as e:
            print(f"   ❌ Error reading alembic_version: {e}")
            print(f"   This might indicate RLS or permissions issue")

        # 4. Check if columns exist
        print(f"\n4. Videos Table Schema Check:")
        try:
            # Check for is_demo column
            result = db.execute(
                text(
                    """
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'videos' 
                    AND column_name IN ('is_demo', 'is_active_demo', 'original_user_id')
                    ORDER BY column_name
                    """
                )
            )
            columns = [row[0] for row in result]
            print(f"   Found columns: {', '.join(columns) if columns else 'None'}")

            expected = ["is_active_demo", "is_demo", "original_user_id"]
            missing = [col for col in expected if col not in columns]
            if missing:
                print(f"   ⚠️  Missing columns: {', '.join(missing)}")
            else:
                print(f"   ✅ All expected columns exist")
        except Exception as e:
            print(f"   ❌ Error checking schema: {e}")

        # 5. Check RLS on alembic_version
        print(f"\n5. Row Level Security Check:")
        try:
            result = db.execute(
                text(
                    """
                    SELECT tablename, rowsecurity 
                    FROM pg_tables 
                    WHERE schemaname = 'public' 
                    AND tablename = 'alembic_version'
                    """
                )
            )
            rls_info = result.fetchone()
            if rls_info:
                print(f"   Table: {rls_info[0]}")
                print(f"   RLS enabled: {rls_info[1]}")
                if rls_info[1]:
                    print(f"   ⚠️  RLS is enabled - check if Alembic has proper permissions")
            else:
                print(f"   ⚠️  Could not find alembic_version table info")
        except Exception as e:
            # Might be SQLite
            if "pg_tables" in str(e):
                print(f"   ℹ️  Not PostgreSQL (or RLS check failed): {e}")
            else:
                print(f"   ❌ Error checking RLS: {e}")

        # 6. Test write to alembic_version (if needed)
        print(f"\n6. Write Test:")
        try:
            # Try to read current version
            result = db.execute(text("SELECT version_num FROM alembic_version"))
            old_version = result.scalar()
            print(f"   Current version in DB: {old_version}")

            # Note: We won't actually write, just check if we can
            print(f"   ✅ Can read alembic_version table")
        except Exception as e:
            print(f"   ❌ Cannot read alembic_version: {e}")
            print(f"   This suggests RLS or permissions issue")

    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()

    print("\n" + "=" * 60)
    print("Recommendations:")
    print("=" * 60)
    print("1. If RLS is enabled on alembic_version, ensure Alembic runs with")
    print("   database owner privileges (not through PostgREST)")
    print("2. Verify SUPABASE_DB_URL points to the correct database")
    print("3. Check if migrations actually ran by verifying columns exist")
    print("4. Try running migrations with explicit transaction commit")
    print("=" * 60)


if __name__ == "__main__":
    check_migration_status()
