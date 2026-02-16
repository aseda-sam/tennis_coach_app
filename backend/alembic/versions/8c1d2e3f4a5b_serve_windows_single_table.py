"""rename serve_attempts to serve_windows and remove proposal table

Revision ID: 8c1d2e3f4a5b
Revises: 1f3b2c9a7e8d
Create Date: 2026-02-20
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "8c1d2e3f4a5b"
down_revision: Union[str, Sequence[str], None] = "1f3b2c9a7e8d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(i["name"] == index_name for i in indexes)


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    if _index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def _create_index_if_missing(
    table_name: str, index_name: str, columns: list[str]
) -> None:
    if not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=False)


def upgrade() -> None:
    """Migrate to single-table serve windows workflow."""
    if _table_exists("serve_attempts"):
        op.rename_table("serve_attempts", "serve_windows")

    # Rename / create canonical indexes for the renamed table.
    _drop_index_if_exists("serve_windows", "ix_serve_attempts_user_created")
    _drop_index_if_exists("serve_windows", "ix_serve_attempts_player_created")
    _drop_index_if_exists("serve_windows", "ix_serve_attempts_user_player_created")
    _drop_index_if_exists("serve_windows", "ix_serve_attempts_user_court_created")
    _drop_index_if_exists("serve_windows", "ix_serve_attempts_video_start")
    _drop_index_if_exists("serve_windows", "ix_serve_attempts_video_id")
    _drop_index_if_exists("serve_windows", "ix_serve_attempts_user_id")
    _drop_index_if_exists("serve_windows", "ix_serve_attempts_player_id")

    _create_index_if_missing(
        "serve_windows", "ix_serve_windows_user_created", ["user_id", "created_at"]
    )
    _create_index_if_missing(
        "serve_windows", "ix_serve_windows_player_created", ["player_id", "created_at"]
    )
    _create_index_if_missing(
        "serve_windows",
        "ix_serve_windows_user_player_created",
        ["user_id", "player_id", "created_at"],
    )
    _create_index_if_missing(
        "serve_windows",
        "ix_serve_windows_user_court_created",
        ["user_id", "court_side", "created_at"],
    )
    _create_index_if_missing(
        "serve_windows", "ix_serve_windows_video_start", ["video_id", "start_timestamp"]
    )
    _create_index_if_missing(
        "serve_windows", "ix_serve_windows_video_status", ["video_id", "status"]
    )

    with op.batch_alter_table("serve_windows") as batch_op:
        batch_op.alter_column("player_id", existing_type=sa.Integer(), nullable=True)

        batch_op.add_column(
            sa.Column("model_version", sa.String(length=50), nullable=True)
        )
        batch_op.add_column(sa.Column("confidence", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("detection_features", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="accepted",
            )
        )
        batch_op.add_column(
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True)
        )

        # Legacy two-table link no longer needed.
        batch_op.drop_column("source_proposal_id")

    op.execute(
        "UPDATE serve_windows SET status='accepted' WHERE status IS NULL OR status=''"
    )

    if _table_exists("serve_window_proposals"):
        op.drop_table("serve_window_proposals")


def downgrade() -> None:
    """Restore proposal table and old serve_attempts naming."""
    if not _table_exists("serve_window_proposals"):
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
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("serve_attempt_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
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

    with op.batch_alter_table("serve_windows") as batch_op:
        batch_op.add_column(
            sa.Column("source_proposal_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            None,
            "serve_window_proposals",
            ["source_proposal_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            op.f("ix_serve_windows_source_proposal_id"),
            ["source_proposal_id"],
            unique=False,
        )

        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("status")
        batch_op.drop_column("detection_features")
        batch_op.drop_column("confidence")
        batch_op.drop_column("model_version")
        batch_op.alter_column("player_id", existing_type=sa.Integer(), nullable=False)

    _drop_index_if_exists("serve_windows", "ix_serve_windows_user_created")
    _drop_index_if_exists("serve_windows", "ix_serve_windows_player_created")
    _drop_index_if_exists("serve_windows", "ix_serve_windows_user_player_created")
    _drop_index_if_exists("serve_windows", "ix_serve_windows_user_court_created")
    _drop_index_if_exists("serve_windows", "ix_serve_windows_video_start")
    _drop_index_if_exists("serve_windows", "ix_serve_windows_video_status")

    _create_index_if_missing(
        "serve_windows", "ix_serve_attempts_user_created", ["user_id", "created_at"]
    )
    _create_index_if_missing(
        "serve_windows", "ix_serve_attempts_player_created", ["player_id", "created_at"]
    )
    _create_index_if_missing(
        "serve_windows",
        "ix_serve_attempts_user_player_created",
        ["user_id", "player_id", "created_at"],
    )
    _create_index_if_missing(
        "serve_windows",
        "ix_serve_attempts_user_court_created",
        ["user_id", "court_side", "created_at"],
    )
    _create_index_if_missing(
        "serve_windows",
        "ix_serve_attempts_video_start",
        ["video_id", "start_timestamp"],
    )

    op.rename_table("serve_windows", "serve_attempts")
