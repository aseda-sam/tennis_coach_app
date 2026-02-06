"""add_knee_bend_metrics_to_serve_attempts

Revision ID: b8bccc14602f
Revises: ea7a68658a52
Create Date: 2026-02-06 21:18:48.432522

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8bccc14602f"
down_revision: Union[str, Sequence[str], None] = "ea7a68658a52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add knee bend metrics columns to serve_attempts table."""
    op.add_column(
        "serve_attempts",
        sa.Column("knee_bend_detected", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "serve_attempts",
        sa.Column("knee_bend_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "serve_attempts",
        sa.Column("knee_hip_ratio_min", sa.Float(), nullable=True),
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


def downgrade() -> None:
    """Remove knee bend metrics columns from serve_attempts table."""
    op.drop_column("serve_attempts", "analysis_version")
    op.drop_column("serve_attempts", "knee_flexion_min_deg_right")
    op.drop_column("serve_attempts", "knee_flexion_min_deg_left")
    op.drop_column("serve_attempts", "knee_hip_ratio_min")
    op.drop_column("serve_attempts", "knee_bend_confidence")
    op.drop_column("serve_attempts", "knee_bend_detected")
