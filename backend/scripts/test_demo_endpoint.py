#!/usr/bin/env python3
"""Test script to verify demo video query works correctly."""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal  # noqa: E402
from app.models.video import Video  # noqa: E402


def test_demo_query() -> None:
    """Test the demo video query logic."""
    db = SessionLocal()
    try:
        # Test the exact query used in the endpoint
        demo = (
            db.query(Video)
            .filter(Video.is_demo)
            .order_by(Video.updated_at.desc())
            .first()
        )

        if demo:
            print("✅ Found demo video:")
            print(f"   ID: {demo.id}")
            print(f"   Filename: {demo.filename}")
            print(f"   is_demo: {demo.is_demo}")
            print(f"   user_id: {demo.user_id}")
            print(f"   updated_at: {demo.updated_at}")
        else:
            print("❌ No demo video found")
            print("\nChecking all videos:")
            all_videos = db.query(Video).all()
            for v in all_videos:
                print(f"   Video {v.id}: is_demo={v.is_demo} (type: {type(v.is_demo)})")

    finally:
        db.close()


if __name__ == "__main__":
    test_demo_query()
