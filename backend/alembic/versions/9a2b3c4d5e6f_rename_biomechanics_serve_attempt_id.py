"""rename serve_biomechanics_reports.serve_attempt_id to serve_window_id

Missed in 8c1d2e3f4a5b when serve_attempts was renamed to serve_windows.

Revision ID: 9a2b3c4d5e6f
Revises: 8c1d2e3f4a5b
Create Date: 2026-02-18
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "9a2b3c4d5e6f"
down_revision: Union[str, Sequence[str], None] = "8c1d2e3f4a5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(c["name"] == column_name for c in inspector.get_columns(table_name))


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(i["name"] == index_name for i in indexes)


def upgrade() -> None:
    """Rename serve_attempt_id → serve_window_id in serve_biomechanics_reports."""
    if _column_exists("serve_biomechanics_reports", "serve_attempt_id"):
        if _index_exists(
            "serve_biomechanics_reports",
            "ix_serve_biomechanics_reports_serve_attempt_id",
        ):
            op.drop_index(
                "ix_serve_biomechanics_reports_serve_attempt_id",
                table_name="serve_biomechanics_reports",
            )

        op.alter_column(
            "serve_biomechanics_reports",
            "serve_attempt_id",
            new_column_name="serve_window_id",
            existing_type=sa.Integer(),
            existing_nullable=False,
        )

        if not _index_exists(
            "serve_biomechanics_reports",
            "ix_serve_biomechanics_reports_serve_window_id",
        ):
            op.create_index(
                "ix_serve_biomechanics_reports_serve_window_id",
                "serve_biomechanics_reports",
                ["serve_window_id"],
                unique=False,
            )


def downgrade() -> None:
    """Rename serve_window_id → serve_attempt_id in serve_biomechanics_reports."""
    if _column_exists("serve_biomechanics_reports", "serve_window_id"):
        if _index_exists(
            "serve_biomechanics_reports",
            "ix_serve_biomechanics_reports_serve_window_id",
        ):
            op.drop_index(
                "ix_serve_biomechanics_reports_serve_window_id",
                table_name="serve_biomechanics_reports",
            )

        op.alter_column(
            "serve_biomechanics_reports",
            "serve_window_id",
            new_column_name="serve_attempt_id",
            existing_type=sa.Integer(),
            existing_nullable=False,
        )

        if not _index_exists(
            "serve_biomechanics_reports",
            "ix_serve_biomechanics_reports_serve_attempt_id",
        ):
            op.create_index(
                "ix_serve_biomechanics_reports_serve_attempt_id",
                "serve_biomechanics_reports",
                ["serve_attempt_id"],
                unique=False,
            )
