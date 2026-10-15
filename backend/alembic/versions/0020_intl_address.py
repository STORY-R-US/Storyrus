"""intl address: country + longer state/region; district optional at app layer

Revision ID: 0020_intl_address
Revises: 0019_user_profile
Create Date: 2026-10-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020_intl_address"
down_revision: Union[str, None] = "0019_user_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("country", sa.String(2), nullable=True))
    # SQLite: ALTER COLUMN limitado — recreate via batch.
    with op.batch_alter_table("users") as batch:
        batch.alter_column(
            "state",
            existing_type=sa.String(2),
            type_=sa.String(80),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.alter_column(
            "state",
            existing_type=sa.String(80),
            type_=sa.String(2),
            existing_nullable=True,
        )
    op.drop_column("users", "country")
