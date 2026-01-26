"""drop_pose_detection_annotated_video_path

Revision ID: 7b3a4c2d1e90
Revises: 1ada01a887ac
Create Date: 2026-01-25 16:05:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b3a4c2d1e90"
down_revision: Union[str, Sequence[str], None] = "1ada01a887ac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Upgrade schema."""
    if "annotated_video_path" in _get_columns("pose_detections"):
        op.drop_column("pose_detections", "annotated_video_path")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "pose_detections",
        sa.Column("annotated_video_path", sa.String(), nullable=True),
    )
