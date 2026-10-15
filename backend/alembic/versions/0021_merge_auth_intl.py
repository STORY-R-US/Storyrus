"""merge alembic heads: password reset + intl address

Revision ID: 0021_merge_auth_intl
Revises: 0020_password_reset, 0020_intl_address
Create Date: 2026-10-05
"""
from typing import Sequence, Union

revision: str = "0021_merge_auth_intl"
down_revision: Union[str, tuple[str, ...], None] = (
    "0020_password_reset",
    "0020_intl_address",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
