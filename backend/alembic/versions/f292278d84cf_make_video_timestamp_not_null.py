"""make_video_timestamp_not_null

Revision ID: f292278d84cf
Revises: 83c750824416
Create Date: 2025-09-01 16:17:02.787399

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f292278d84cf"
down_revision: Union[str, Sequence[str], None] = "83c750824416"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite doesn't support ALTER COLUMN for nullable constraints
    # We need to recreate the table with the new constraint

    # Create new table with NOT NULL constraint
    op.create_table(
        "ball_contacts_new",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("frame_number", sa.Integer(), nullable=True),
        sa.Column("video_timestamp", sa.Float(), nullable=False),
        sa.Column("player", sa.Integer(), nullable=True),
        sa.Column("stroke_type", sa.String(), nullable=True),
        sa.Column("stroke_subtype", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("ball_position", sa.String(), nullable=True),
        sa.Column("player_position", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ball_area", sa.Float(), nullable=True),
        sa.Column("ball_size_factor", sa.Float(), nullable=True),
        sa.Column("racket_data", sa.String(), nullable=True),
        sa.Column("ball_bbox", sa.String(), nullable=True),
        sa.Column("ball_racket_distance", sa.Float(), nullable=True),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("detection_source", sa.String(length=20), nullable=False),
        sa.Column("contact_hand", sa.String(length=10), nullable=True),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Copy data from old table to new table
    op.execute("""
        INSERT INTO ball_contacts_new 
        SELECT * FROM ball_contacts
    """)

    # Drop old table
    op.drop_table("ball_contacts")

    # Rename new table to original name
    op.rename_table("ball_contacts_new", "ball_contacts")

    # Recreate indexes
    op.create_index(op.f("ix_ball_contacts_id"), "ball_contacts", ["id"], unique=False)
    op.create_index(
        op.f("ix_ball_contacts_frame_number"),
        "ball_contacts",
        ["frame_number"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ball_contacts_video_id"), "ball_contacts", ["video_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate table with nullable constraint
    op.create_table(
        "ball_contacts_old",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("frame_number", sa.Integer(), nullable=True),
        sa.Column("video_timestamp", sa.Float(), nullable=True),
        sa.Column("player", sa.Integer(), nullable=True),
        sa.Column("stroke_type", sa.String(), nullable=True),
        sa.Column("stroke_subtype", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("ball_position", sa.String(), nullable=True),
        sa.Column("player_position", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ball_area", sa.Float(), nullable=True),
        sa.Column("ball_size_factor", sa.Float(), nullable=True),
        sa.Column("racket_data", sa.String(), nullable=True),
        sa.Column("ball_bbox", sa.String(), nullable=True),
        sa.Column("ball_racket_distance", sa.Float(), nullable=True),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("detection_source", sa.String(length=20), nullable=False),
        sa.Column("contact_hand", sa.String(length=10), nullable=True),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Copy data back
    op.execute("""
        INSERT INTO ball_contacts_old 
        SELECT * FROM ball_contacts
    """)

    # Drop current table
    op.drop_table("ball_contacts")

    # Rename old table back
    op.rename_table("ball_contacts_old", "ball_contacts")

    # Recreate indexes
    op.create_index(op.f("ix_ball_contacts_id"), "ball_contacts", ["id"], unique=False)
    op.create_index(
        op.f("ix_ball_contacts_frame_number"),
        "ball_contacts",
        ["frame_number"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ball_contacts_video_id"), "ball_contacts", ["video_id"], unique=False
    )
