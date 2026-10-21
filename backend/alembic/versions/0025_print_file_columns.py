"""Repair print_orders created with the original single file_key column.

Revision ID: 0025_print_file_columns
Revises: 0024_project_preview_notified

0018 was changed after deployment to split the print PDFs. Existing databases
still have file_key, so upgrading the edited 0018 never added these columns.
Keep legacy files and add only the missing nullable columns.
"""

import sqlalchemy as sa

from alembic import op

revision = "0025_print_file_columns"
down_revision = "0024_project_preview_notified"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("print_orders")}
    for name in ("cover_key", "interior_key"):
        if name not in columns:
            op.add_column("print_orders", sa.Column(name, sa.Text(), nullable=True))


def downgrade() -> None:
    # 0018 now declares these columns too. Keep PDFs and compatibility with it.
    pass
