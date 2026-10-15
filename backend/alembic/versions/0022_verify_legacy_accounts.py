"""Verify legacy registered accounts created before email confirmation.

Revision ID: 0022_verify_legacy_accounts
Revises: 0021_merge_auth_intl
Create Date: 2026-10-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0022_verify_legacy_accounts"
down_revision: Union[str, None] = "0021_merge_auth_intl"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Contas reais anteriores à verificação de e-mail ficaram com
    # email_verified_at NULL e sem token pendente — o login 403 travava o estúdio.
    op.execute(
        """
        UPDATE users
        SET email_verified_at = CURRENT_TIMESTAMP
        WHERE email_verified_at IS NULL
          AND email_verify_token_hash IS NULL
          AND password_hash <> '!guest'
          AND email NOT LIKE 'guest-%@storyrus.app'
        """
    )


def downgrade() -> None:
    pass
