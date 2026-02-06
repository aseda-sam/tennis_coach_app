"""merge_572faf3d602_and_add_stage_tracking

Revision ID: ea7a68658a52
Revises: 572faf3d602, add_stage_tracking
Create Date: 2026-02-04 17:10:57.956718

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "ea7a68658a52"
down_revision: Union[str, Sequence[str], None] = ("572faf3d602", "add_stage_tracking")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
