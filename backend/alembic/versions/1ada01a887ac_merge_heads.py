"""merge heads

Revision ID: 1ada01a887ac
Revises: c40e21e8c84e, f2f8e3a9b1c7
Create Date: 2026-01-25 17:27:57.700979

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "1ada01a887ac"
down_revision: Union[str, Sequence[str], None] = ("c40e21e8c84e", "f2f8e3a9b1c7")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
