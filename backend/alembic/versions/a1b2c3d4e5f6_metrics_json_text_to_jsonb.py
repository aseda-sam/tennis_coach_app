"""Migrate metrics_json TEXT to metrics JSONB nested by phase.

Replaces the flat TEXT column metrics_json with a JSONB column metrics
using nested-by-phase structure: {"loading": {"knee_flexion_min_deg": 95.5}, ...}

This enables SQL cross-serve queries on metric values and bakes the phase
relationship into the stored data.

Revision ID: a1b2c3d4e5f6
Revises: 60c30a2a5c01
Create Date: 2026-02-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "60c30a2a5c01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add metrics JSONB column, migrate data from metrics_json TEXT, drop TEXT column."""
    op.add_column(
        "serve_biomechanics_reports",
        sa.Column("metrics", JSONB, nullable=True),
    )

    # Migrate existing flat TEXT → nested JSONB
    op.execute(
        sa.text("""
            UPDATE serve_biomechanics_reports
            SET metrics = jsonb_build_object(
                'loading', jsonb_strip_nulls(jsonb_build_object(
                    'knee_flexion_min_deg',
                    CASE
                        WHEN metrics_json::jsonb->>'knee_flexion_min_deg' IS NOT NULL
                        THEN (metrics_json::jsonb->>'knee_flexion_min_deg')::float
                        ELSE NULL
                    END
                )),
                'release', jsonb_strip_nulls(jsonb_build_object(
                    'toss_peak_height',
                    CASE
                        WHEN metrics_json::jsonb->>'toss_peak_height' IS NOT NULL
                        THEN (metrics_json::jsonb->>'toss_peak_height')::float
                        ELSE NULL
                    END,
                    'toss_laterality',
                    CASE
                        WHEN metrics_json::jsonb->>'toss_laterality' IS NOT NULL
                        THEN (metrics_json::jsonb->>'toss_laterality')::float
                        ELSE NULL
                    END
                ))
            )
            WHERE metrics_json IS NOT NULL AND metrics_json != 'null'
        """)
    )

    op.drop_column("serve_biomechanics_reports", "metrics_json")


def downgrade() -> None:
    """Re-add metrics_json TEXT, flatten JSONB back to text, drop JSONB column."""
    op.add_column(
        "serve_biomechanics_reports",
        sa.Column("metrics_json", sa.Text(), nullable=True),
    )

    # Flatten nested JSONB → flat TEXT JSON
    op.execute(
        sa.text("""
            UPDATE serve_biomechanics_reports
            SET metrics_json = (
                jsonb_strip_nulls(jsonb_build_object(
                    'knee_flexion_min_deg', metrics->'loading'->'knee_flexion_min_deg',
                    'toss_peak_height',     metrics->'release'->'toss_peak_height',
                    'toss_laterality',      metrics->'release'->'toss_laterality'
                ))
            )::text
            WHERE metrics IS NOT NULL
        """)
    )

    op.drop_column("serve_biomechanics_reports", "metrics")
