"""drop_ball_contacts_table

Revision ID: 3f2a1c9d7b10
Revises: e585518be299
Create Date: 2026-01-25 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f2a1c9d7b10"
down_revision: Union[str, Sequence[str], None] = "e585518be299"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table("ball_contacts")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "ball_contacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("frame_number", sa.Integer(), nullable=True),
        sa.Column("video_timestamp", sa.Float(), nullable=False),
        sa.Column("contact_hand", sa.String(length=10), nullable=True),
        sa.Column("stroke_type", sa.String(), nullable=True),
        sa.Column("stroke_subtype", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detection_source", sa.String(length=20), nullable=False),
        sa.Column("elbow_angle", sa.Float(), nullable=True),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ball_contacts_frame_number"),
        "ball_contacts",
        ["frame_number"],
        unique=False,
    )
    op.create_index(op.f("ix_ball_contacts_id"), "ball_contacts", ["id"], unique=False)
    op.create_index(
        op.f("ix_ball_contacts_player_id"), "ball_contacts", ["player_id"], unique=False
    )
    op.create_index(
        op.f("ix_ball_contacts_video_id"), "ball_contacts", ["video_id"], unique=False
    )
