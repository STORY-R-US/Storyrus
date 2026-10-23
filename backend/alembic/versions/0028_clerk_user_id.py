"""Liga a conta local ao usuário do Clerk sem trocar users.id."""

import sqlalchemy as sa

from alembic import op

revision = "0028_clerk_user_id"
down_revision = "0027_purchase_flow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("clerk_user_id", sa.String(length=64), nullable=True))
    op.create_index("ix_users_clerk_user_id", "users", ["clerk_user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_clerk_user_id", table_name="users")
    op.drop_column("users", "clerk_user_id")
