"""cleanup_invalid_stroke_subtypes

Revision ID: d55e25138d67
Revises: d30414b42ecb
Create Date: 2026-01-15 16:55:13.364337

"""
import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
from app.core.shot_types import (
    is_valid_subtype_for_type,
    map_legacy_subtype_to_canonical,
)

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = 'd55e25138d67'
down_revision: Union[str, Sequence[str], None] = 'd30414b42ecb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate legacy stroke subtypes to canonical subtypes.

    This migration maps legacy free-text subtypes (e.g., "forehand", "backhand")
    to canonical subtypes based on stroke_type. If a mapping exists, the subtype
    is updated. If no mapping is possible, the subtype is set to NULL.

    Examples:
        - "forehand" + "ground_stroke" → "forehand_flat"
        - "forehand" + "return" → "forehand" (already valid, no change)
        - "forehand" + "volley" → "forehand" (already valid, no change)
        - "topspin" + "ground_stroke" → NULL (can't determine forehand vs backhand)
    """
    bind = op.get_bind()

    # Query all contacts with non-null subtypes
    result = bind.execute(
        sa.text("""
            SELECT id, stroke_type, stroke_subtype
            FROM ball_contacts
            WHERE stroke_subtype IS NOT NULL AND stroke_subtype != ''
        """)
    )

    contacts = result.fetchall()
    mapped_count = 0
    cleared_count = 0

    for contact_id, stroke_type, stroke_subtype in contacts:
        # Check if subtype is already valid (no change needed)
        if is_valid_subtype_for_type(stroke_type, stroke_subtype):
            continue

        # Try to map legacy subtype to canonical
        canonical_subtype = map_legacy_subtype_to_canonical(
            stroke_type, stroke_subtype
        )

        if canonical_subtype:
            # Update to mapped canonical subtype
            bind.execute(
                sa.text("""
                    UPDATE ball_contacts
                    SET stroke_subtype = :canonical_subtype
                    WHERE id = :contact_id
                """),
                {
                    "canonical_subtype": canonical_subtype,
                    "contact_id": contact_id,
                },
            )
            mapped_count += 1
            logger.info(
                f"Mapped subtype '{stroke_subtype}' → '{canonical_subtype}' "
                f"for stroke_type '{stroke_type}' in ball_contact {contact_id}"
            )
        else:
            # No mapping possible, set to NULL
            bind.execute(
                sa.text("""
                    UPDATE ball_contacts
                    SET stroke_subtype = NULL
                    WHERE id = :contact_id
                """),
                {"contact_id": contact_id},
            )
            cleared_count += 1
            logger.info(
                f"Cleared unmappable subtype '{stroke_subtype}' "
                f"for stroke_type '{stroke_type}' in ball_contact {contact_id}"
            )

    if mapped_count > 0 or cleared_count > 0:
        logger.info(
            f"Migration completed: mapped {mapped_count} subtypes, "
            f"cleared {cleared_count} unmappable subtypes"
        )
    else:
        logger.info("Migration completed: no invalid stroke subtypes found")

    bind.commit()


def downgrade() -> None:
    """Downgrade schema.

    Note: This migration cannot be reversed as we don't store the original
    invalid subtype values. The data loss is acceptable as these were
    invalid values that would cause validation errors.
    """
    pass
