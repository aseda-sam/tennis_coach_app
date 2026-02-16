"""replace serve_feedback_reports with serve_biomechanics_reports

Revision ID: 66b306db700e
Revises: 55a205ca699d
Create Date: 2026-02-16

Drops serve_feedback_reports and creates simplified serve_biomechanics_reports
(phases + raw metrics only, no scoring/coaching).
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "66b306db700e"
down_revision: Union[str, Sequence[str], None] = "55a205ca699d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop old table, create new simplified serve_biomechanics_reports."""
    op.drop_table("serve_feedback_reports")

    op.create_table(
        "serve_biomechanics_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("serve_attempt_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("phase_segmentation_json", sa.Text(), nullable=True),
        sa.Column("metrics_json", sa.Text(), nullable=True),
        sa.Column("analysis_version", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["serve_attempt_id"], ["serve_attempts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_serve_biomechanics_reports_id"),
        "serve_biomechanics_reports",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_serve_biomechanics_reports_serve_attempt_id"),
        "serve_biomechanics_reports",
        ["serve_attempt_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_serve_biomechanics_reports_user_id"),
        "serve_biomechanics_reports",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_biomechanics_reports_player_created",
        "serve_biomechanics_reports",
        ["player_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_biomechanics_reports_user_player",
        "serve_biomechanics_reports",
        ["user_id", "player_id"],
        unique=False,
    )


def downgrade() -> None:
    """Restore serve_feedback_reports, drop serve_biomechanics_reports."""
    op.drop_table("serve_biomechanics_reports")

    op.create_table(
        "serve_feedback_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("serve_attempt_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("overall_rating", sa.String(length=20), nullable=True),
        sa.Column("phase_scores_json", sa.Text(), nullable=True),
        sa.Column("metrics_json", sa.Text(), nullable=True),
        sa.Column("phase_segmentation_json", sa.Text(), nullable=True),
        sa.Column("injury_risk_flags_json", sa.Text(), nullable=True),
        sa.Column("top_priority", sa.String(length=100), nullable=True),
        sa.Column("analysis_version", sa.String(length=20), nullable=False),
        sa.Column("thresholds_version", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["serve_attempt_id"], ["serve_attempts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_feedback_reports_player_created",
        "serve_feedback_reports",
        ["player_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_reports_user_player",
        "serve_feedback_reports",
        ["user_id", "player_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_serve_feedback_reports_id"),
        "serve_feedback_reports",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_serve_feedback_reports_serve_attempt_id"),
        "serve_feedback_reports",
        ["serve_attempt_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_serve_feedback_reports_user_id"),
        "serve_feedback_reports",
        ["user_id"],
        unique=False,
    )
