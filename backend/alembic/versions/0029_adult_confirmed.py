"""Declaração de conta adulta (18+) para o COPPA."""

import sqlalchemy as sa

from alembic import op

revision = "0029_adult_confirmed"
down_revision = "0028_clerk_user_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("adult_confirmed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "adult_confirmed_at")
