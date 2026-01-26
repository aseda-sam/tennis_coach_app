"""fix_player_id_foreign_key_constraint

Revision ID: 439323fac421
Revises: 7b3a4c2d1e90
Create Date: 2026-01-26 11:52:21.445441

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "439323fac421"
down_revision: Union[str, Sequence[str], None] = "7b3a4c2d1e90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        # SQLite: Use batch_alter_table to recreate the foreign key constraint
        # SQLite doesn't support dropping constraints directly, so Alembic recreates the table
        # We just create the new constraint - Alembic will recreate the table with it,
        # automatically replacing any old constraint
        with op.batch_alter_table("serve_attempts", schema=None) as batch_op:
            # Create new foreign key constraint with CASCADE
            # Alembic's batch mode will recreate the table with this constraint,
            # replacing any existing foreign key constraint on player_id
            batch_op.create_foreign_key(
                "serve_attempts_player_id_fkey",
                "players",
                ["player_id"],
                ["id"],
                ondelete="CASCADE",
            )
    else:
        # PostgreSQL: Use direct operations
        # Drop the existing foreign key constraint with SET NULL
        op.drop_constraint(
            "serve_attempts_player_id_fkey",
            "serve_attempts",
            type_="foreignkey",
        )
        # Create new foreign key constraint with CASCADE
        op.create_foreign_key(
            "serve_attempts_player_id_fkey",
            "serve_attempts",
            "players",
            ["player_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        # SQLite: Use batch_alter_table to recreate the foreign key constraint
        with op.batch_alter_table("serve_attempts", schema=None) as batch_op:
            # Restore the SET NULL constraint (even though it's invalid with nullable=False)
            # Alembic's batch mode will recreate the table with this constraint,
            # replacing any existing foreign key constraint on player_id
            batch_op.create_foreign_key(
                "serve_attempts_player_id_fkey",
                "players",
                ["player_id"],
                ["id"],
                ondelete="SET NULL",
            )
    else:
        # PostgreSQL: Use direct operations
        # Drop the CASCADE constraint
        op.drop_constraint(
            "serve_attempts_player_id_fkey",
            "serve_attempts",
            type_="foreignkey",
        )
        # Restore the SET NULL constraint (even though it's invalid with nullable=False)
        op.create_foreign_key(
            "serve_attempts_player_id_fkey",
            "serve_attempts",
            "players",
            ["player_id"],
            ["id"],
            ondelete="SET NULL",
        )
