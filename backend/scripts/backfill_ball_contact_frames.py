#!/usr/bin/env python3
"""
Backfill script to populate frame_number for existing ball contacts.

This script calculates and stores frame_number for all existing ball contacts
that don't already have this field populated, using the formula:
frame_number = round(video_timestamp * video.fps)

Usage:
    python scripts/backfill_ball_contact_frames.py
"""

import logging
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.ball_contact import BallContact
from app.models.video import Video

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def backfill_ball_contact_frames() -> None:
    """
    Backfill frame_number for all ball contacts that don't have it set.

    This function:
    1. Finds all ball contacts with null frame_number
    2. Gets the associated video's FPS
    3. Calculates frame_number = round(video_timestamp * fps)
    4. Updates the database record
    """
    db: Session = next(get_db())

    try:
        # Find all ball contacts without frame_number
        contacts_to_update = (
            db.query(BallContact).filter(BallContact.frame_number.is_(None)).all()
        )

        logger.info(f"Found {len(contacts_to_update)} ball contacts to backfill")

        if not contacts_to_update:
            logger.info("No ball contacts need frame_number backfill")
            return

        updated_count = 0
        skipped_count = 0

        for contact in contacts_to_update:
            try:
                # Get the associated video
                video = db.query(Video).filter(Video.id == contact.video_id).first()

                if not video:
                    logger.warning(
                        f"Video {contact.video_id} not found for contact {contact.id}"
                    )
                    skipped_count += 1
                    continue

                if not video.fps or video.fps <= 0:
                    logger.warning(
                        f"Video {video.id} has invalid FPS ({video.fps}) for contact {contact.id}"
                    )
                    skipped_count += 1
                    continue

                # Calculate frame number
                frame_number = round(contact.video_timestamp * video.fps)

                # Update the contact
                contact.frame_number = frame_number
                updated_count += 1

                logger.debug(
                    f"Updated contact {contact.id}: "
                    f"timestamp={contact.video_timestamp:.3f}s, "
                    f"fps={video.fps}, "
                    f"frame_number={frame_number}"
                )

            except Exception as e:
                logger.error(f"Error processing contact {contact.id}: {e}")
                skipped_count += 1
                continue

        # Commit all changes
        db.commit()

        logger.info("Backfill completed:")
        logger.info(f"  - Updated: {updated_count} contacts")
        logger.info(f"  - Skipped: {skipped_count} contacts")

    except Exception as e:
        logger.error(f"Error during backfill: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    """Main entry point for the backfill script."""
    logger.info("Starting ball contact frame_number backfill")

    try:
        backfill_ball_contact_frames()
        logger.info("Backfill completed successfully")
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
