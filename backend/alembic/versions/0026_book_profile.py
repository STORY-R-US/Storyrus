"""Persist the Studio book profile and explicit approval stages."""

import sqlalchemy as sa

from alembic import op

revision = "0026_book_profile"
down_revision = "0025_print_file_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("book_profile", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "book_profile")
