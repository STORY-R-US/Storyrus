"""Add users.is_admin for owner panels.

Revision ID: 0023_user_is_admin
Revises: 0022_verify_legacy_accounts
Create Date: 2026-10-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0023_user_is_admin"
down_revision: Union[str, None] = "0022_verify_legacy_accounts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Bootstrap da conta já usada em OWNER_EMAILS / render.yaml.
    # Outros admins: UPDATE users SET is_admin = true WHERE lower(email) = '...';
    op.execute(
        """
        UPDATE users
        SET is_admin = true
        WHERE lower(email) = 'eng.andrevitor89@gmail.com'
        """
    )


def downgrade() -> None:
    op.drop_column("users", "is_admin")
