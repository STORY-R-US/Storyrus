"""Mapa das contas para a troca da instância do Clerk (dev → produção)."""

import sqlalchemy as sa

from alembic import op
from app.models import GUID

revision = "0032_clerk_account_map"
down_revision = "0031_asset_kind_length"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clerk_account_map",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "user_id",
            GUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dev_clerk_user_id", sa.String(64), nullable=True),
        sa.Column("prod_clerk_user_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="staged"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_clerk_account_map_user_id", "clerk_account_map", ["user_id"], unique=True)
    op.create_index(
        "ix_clerk_account_map_prod_clerk_user_id",
        "clerk_account_map",
        ["prod_clerk_user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_clerk_account_map_prod_clerk_user_id", table_name="clerk_account_map")
    op.drop_index("ix_clerk_account_map_user_id", table_name="clerk_account_map")
    op.drop_table("clerk_account_map")
