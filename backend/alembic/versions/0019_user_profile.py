"""user profile: nome, telefone, endereco, terms, email_verified

Revision ID: 0019_user_profile
Revises: 0018_print_orders
Create Date: 2026-10-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019_user_profile"
down_revision: Union[str, None] = "0018_print_orders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(120), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("postal_code", sa.String(16), nullable=True))
    op.add_column("users", sa.Column("street", sa.String(160), nullable=True))
    op.add_column("users", sa.Column("number", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("complement", sa.String(80), nullable=True))
    op.add_column("users", sa.Column("district", sa.String(80), nullable=True))
    op.add_column("users", sa.Column("city", sa.String(80), nullable=True))
    op.add_column("users", sa.Column("state", sa.String(2), nullable=True))
    op.add_column("users", sa.Column("terms_accepted_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("email_verify_token_hash", sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "email_verify_token_hash")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "terms_accepted_at")
    op.drop_column("users", "state")
    op.drop_column("users", "city")
    op.drop_column("users", "district")
    op.drop_column("users", "complement")
    op.drop_column("users", "number")
    op.drop_column("users", "street")
    op.drop_column("users", "postal_code")
    op.drop_column("users", "phone")
    op.drop_column("users", "full_name")
