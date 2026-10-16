"""Persist customer preview approval separately from final print approval."""

import sqlalchemy as sa

from alembic import op

revision = "0027_purchase_flow"
down_revision = "0026_book_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("purchase_flow", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "purchase_flow")
