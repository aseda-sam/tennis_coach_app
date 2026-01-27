"""merge_video_jobs_migration

Revision ID: 7a1eaf7c970e
Revises: 0c9bd8a4de2c, 439323fac421
Create Date: 2026-01-27 19:12:25.373613

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "7a1eaf7c970e"
down_revision: Union[str, Sequence[str], None] = ("0c9bd8a4de2c", "439323fac421")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
