"""backfill contact_source auto for existing rows

Revision ID: 2cf2e7b95cd1
Revises: be238e4d58d4
Create Date: 2026-02-23 16:56:06.148847

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2cf2e7b95cd1"
down_revision: Union[str, Sequence[str], None] = "be238e4d58d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Backfill contact_source = 'auto' for all pre-existing rows.

    All contact_timestamp values that existed before the contact_source column was
    introduced were set by the auto-detection pipeline (ball detection RQ, scout/refine
    pipeline, or biomechanics lazy fallback). The manual contact button was only added
    after the column was introduced, so NULL rows are unambiguously 'auto'.
    """
    op.execute(
        """
        UPDATE serve_windows
        SET contact_source = 'auto'
        WHERE contact_timestamp IS NOT NULL
          AND contact_source IS NULL
        """
    )


def downgrade() -> None:
    """Revert backfill — restore NULL for rows that were auto-backfilled."""
    op.execute(
        """
        UPDATE serve_windows
        SET contact_source = NULL
        WHERE contact_source = 'auto'
        """
    )
