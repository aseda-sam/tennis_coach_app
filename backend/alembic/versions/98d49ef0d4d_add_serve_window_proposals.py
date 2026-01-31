"""add_serve_window_proposals

Revision ID: 98d49ef0d4d
Revises: 7d36585465af
Create Date: 2026-01-30 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "98d49ef0d4d"
down_revision: Union[str, Sequence[str], None] = "7d36585465af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    assert (revision, down_revision, branch_labels, depends_on)  # noqa: F631 - read by Alembic
    # Create serve_window_proposals table
    op.create_table(
        "serve_window_proposals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("start_timestamp", sa.Float(), nullable=False),
        sa.Column("end_timestamp", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("detection_features", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="pending"
        ),
        sa.Column("serve_attempt_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["serve_attempt_id"], ["serve_attempts.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_serve_window_proposals_id"),
        "serve_window_proposals",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_serve_window_proposals_video_id"),
        "serve_window_proposals",
        ["video_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_serve_window_proposals_user_id"),
        "serve_window_proposals",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_serve_window_proposals_video_status",
        "serve_window_proposals",
        ["video_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_serve_window_proposals_user_created",
        "serve_window_proposals",
        ["user_id", "created_at"],
        unique=False,
    )

    # Add provenance columns to serve_attempts table
    op.add_column(
        "serve_attempts",
        sa.Column(
            "source", sa.String(length=20), nullable=False, server_default="manual"
        ),
    )
    op.add_column(
        "serve_attempts",
        sa.Column("source_proposal_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "serve_attempts",
        sa.Column("original_start_timestamp", sa.Float(), nullable=True),
    )
    op.add_column(
        "serve_attempts",
        sa.Column("original_end_timestamp", sa.Float(), nullable=True),
    )
    op.create_foreign_key(
        "fk_serve_attempts_source_proposal",
        "serve_attempts",
        "serve_window_proposals",
        ["source_proposal_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove foreign key and columns from serve_attempts
    op.drop_constraint(
        "fk_serve_attempts_source_proposal", "serve_attempts", type_="foreignkey"
    )
    op.drop_column("serve_attempts", "original_end_timestamp")
    op.drop_column("serve_attempts", "original_start_timestamp")
    op.drop_column("serve_attempts", "source_proposal_id")
    op.drop_column("serve_attempts", "source")

    # Drop serve_window_proposals table
    op.drop_index(
        "ix_serve_window_proposals_user_created", table_name="serve_window_proposals"
    )
    op.drop_index(
        "ix_serve_window_proposals_video_status", table_name="serve_window_proposals"
    )
    op.drop_index(
        op.f("ix_serve_window_proposals_user_id"), table_name="serve_window_proposals"
    )
    op.drop_index(
        op.f("ix_serve_window_proposals_video_id"), table_name="serve_window_proposals"
    )
    op.drop_index(
        op.f("ix_serve_window_proposals_id"), table_name="serve_window_proposals"
    )
    op.drop_table("serve_window_proposals")
