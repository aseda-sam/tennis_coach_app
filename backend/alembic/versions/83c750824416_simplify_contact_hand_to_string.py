"""simplify_contact_hand_to_string

Revision ID: 83c750824416
Revises: 5c0f78d9bd09
Create Date: 2025-09-01 12:32:15.001889

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "83c750824416"
down_revision: Union[str, Sequence[str], None] = "5c0f78d9bd09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Convert enum column to string column
    # First, create a new string column
    op.add_column(
        "ball_contacts", sa.Column("contact_hand_new", sa.String(10), nullable=True)
    )

    # Copy data from enum to string (convert enum values to strings)
    op.execute("""
        UPDATE ball_contacts 
        SET contact_hand_new = CASE 
            WHEN contact_hand = 'left' THEN 'left'
            WHEN contact_hand = 'right' THEN 'right'
            ELSE NULL
        END
    """)

    # Drop the old enum column
    op.drop_column("ball_contacts", "contact_hand")

    # Rename the new column to the original name
    op.alter_column("ball_contacts", "contact_hand_new", new_column_name="contact_hand")


def downgrade() -> None:
    """Downgrade schema."""
    # Convert back to enum (this is simplified - you'd need to recreate the enum type)
    # For now, we'll just convert the string column back
    op.execute("""
        UPDATE ball_contacts 
        SET contact_hand = CASE 
            WHEN contact_hand = 'left' THEN 'left'
            WHEN contact_hand = 'right' THEN 'right'
            ELSE NULL
        END
    """)
