"""drop legacy serve attempt metrics

Revision ID: 1f3b2c9a7e8d
Revises: 66b306db700e
Create Date: 2026-02-20
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "1f3b2c9a7e8d"
down_revision: Union[str, Sequence[str], None] = "66b306db700e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop legacy per-serve metrics stored on serve_attempts."""
    op.drop_column("serve_attempts", "elbow_angle_at_contact")
    op.drop_column("serve_attempts", "knee_bend_detected")
    op.drop_column("serve_attempts", "knee_bend_confidence")
    op.drop_column("serve_attempts", "knee_hip_ratio_min")
    op.drop_column("serve_attempts", "knee_flexion_min_deg_left")
    op.drop_column("serve_attempts", "knee_flexion_min_deg_right")
    op.drop_column("serve_attempts", "analysis_version")
    op.drop_column("serve_attempts", "toss_peak_height")
    op.drop_column("serve_attempts", "toss_peak_timestamp")


def downgrade() -> None:
    """Restore legacy per-serve metrics on serve_attempts."""
    op.add_column(
        "serve_attempts", sa.Column("elbow_angle_at_contact", sa.Float(), nullable=True)
    )
    op.add_column(
        "serve_attempts", sa.Column("knee_bend_detected", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "serve_attempts", sa.Column("knee_bend_confidence", sa.Float(), nullable=True)
    )
    op.add_column(
        "serve_attempts", sa.Column("knee_hip_ratio_min", sa.Float(), nullable=True)
    )
    op.add_column(
        "serve_attempts",
        sa.Column("knee_flexion_min_deg_left", sa.Float(), nullable=True),
    )
    op.add_column(
        "serve_attempts",
        sa.Column("knee_flexion_min_deg_right", sa.Float(), nullable=True),
    )
    op.add_column(
        "serve_attempts",
        sa.Column("analysis_version", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "serve_attempts", sa.Column("toss_peak_height", sa.Float(), nullable=True)
    )
    op.add_column(
        "serve_attempts", sa.Column("toss_peak_timestamp", sa.Float(), nullable=True)
    )
