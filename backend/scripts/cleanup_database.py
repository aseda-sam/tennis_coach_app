#!/usr/bin/env python3
"""
Database cleanup script for ball contact migration.

This script deletes all existing videos, analyses, and ball contacts
to start fresh with the new ball contact system.
"""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.ball_contact import BallContact
from app.models.video import Video


def cleanup_database():
    """Clean up all existing data to start fresh."""
    print("🧹 Starting database cleanup...")

    # Get database session
    db = next(get_db())

    try:
        # 1. Delete all ball contacts
        ball_contacts_count = db.query(BallContact).count()
        db.query(BallContact).delete()
        print(f"   ✅ Deleted {ball_contacts_count} ball contacts")

        # 2. Delete all analyses
        analyses_count = db.query(Analysis).count()
        db.query(Analysis).delete()
        print(f"   ✅ Deleted {analyses_count} analyses")

        # 3. Delete all videos
        videos_count = db.query(Video).count()
        db.query(Video).delete()
        print(f"   ✅ Deleted {videos_count} videos")

        # 4. Commit changes
        db.commit()

        print("\n🎉 Database cleaned successfully!")
        print(f"   - Deleted {videos_count} videos")
        print(f"   - Deleted {analyses_count} analyses")
        print(f"   - Deleted {ball_contacts_count} ball contacts")
        print("\n📝 Ready for fresh data with the new ball contact system!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error during cleanup: {e}")
        sys.exit(1)
    finally:
        db.close()


def verify_cleanup():
    """Verify that the database is clean."""
    print("\n🔍 Verifying cleanup...")

    db = next(get_db())

    try:
        # Check counts
        videos_count = db.query(Video).count()
        analyses_count = db.query(Analysis).count()
        ball_contacts_count = db.query(BallContact).count()

        print("   📊 Current database state:")
        print(f"      - Videos: {videos_count}")
        print(f"      - Analyses: {analyses_count}")
        print(f"      - Ball Contacts: {ball_contacts_count}")

        if videos_count == 0 and analyses_count == 0 and ball_contacts_count == 0:
            print("   ✅ Database is clean and ready!")
            return True
        else:
            print("   ❌ Database still contains data!")
            return False

    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Ball Contact Migration - Database Cleanup")
    print("=" * 50)

    # Confirm with user
    response = input(
        "\n⚠️  This will DELETE ALL existing data. Are you sure? (yes/no): "
    )
    if response.lower() != "yes":
        print("❌ Cleanup cancelled.")
        sys.exit(0)

    # Perform cleanup
    cleanup_database()

    # Verify cleanup
    if verify_cleanup():
        print("\n🎯 Migration Phase 4 Complete!")
        print("   Ready to test the new ball contact system with fresh data.")
    else:
        print("\n❌ Cleanup verification failed!")
        sys.exit(1)
