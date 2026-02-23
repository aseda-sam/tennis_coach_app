"""Rename phase values: trophy→cocking, follow_through→finish in stored JSON.

Aligns phase names with Kovacs (2011) 8-stage model:
  Stage 4: Cocking (was "Trophy" — trophy is a pose, not a phase)
  Stage 8: Finish  (was "Follow-through")

Also renames metric keys that referenced "trophy":
  trunk_rotation_at_trophy     → trunk_rotation_at_cocking
  shoulder_abduction_at_trophy → shoulder_abduction_at_cocking

Revision ID: 60c30a2a5c01
Revises: 9a2b3c4d5e6f
Create Date: 2026-02-18
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "60c30a2a5c01"
down_revision: Union[str, None] = "9a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Phase names in phase_segmentation_json
    op.execute(
        sa.text("""
            UPDATE serve_biomechanics_reports
            SET phase_segmentation_json = REPLACE(
                REPLACE(phase_segmentation_json,
                    '"follow_through"', '"finish"'),
                '"trophy"', '"cocking"')
            WHERE phase_segmentation_json IS NOT NULL
        """)
    )

    # Metric keys in metrics_json
    op.execute(
        sa.text("""
            UPDATE serve_biomechanics_reports
            SET metrics_json = REPLACE(
                REPLACE(metrics_json,
                    'shoulder_abduction_at_trophy', 'shoulder_abduction_at_cocking'),
                'trunk_rotation_at_trophy', 'trunk_rotation_at_cocking')
            WHERE metrics_json IS NOT NULL
        """)
    )


def downgrade() -> None:
    op.execute(
        sa.text("""
            UPDATE serve_biomechanics_reports
            SET phase_segmentation_json = REPLACE(
                REPLACE(phase_segmentation_json,
                    '"finish"', '"follow_through"'),
                '"cocking"', '"trophy"')
            WHERE phase_segmentation_json IS NOT NULL
        """)
    )

    op.execute(
        sa.text("""
            UPDATE serve_biomechanics_reports
            SET metrics_json = REPLACE(
                REPLACE(metrics_json,
                    'shoulder_abduction_at_cocking', 'shoulder_abduction_at_trophy'),
                'trunk_rotation_at_cocking', 'trunk_rotation_at_trophy')
            WHERE metrics_json IS NOT NULL
        """)
    )
