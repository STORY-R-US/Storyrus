"""project: tamanho impresso M ou P

Revision ID: 0015_project_book_size
Revises: 0014_jobs_request_id
Create Date: 2026-09-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015_project_book_size"
down_revision: Union[str, None] = "0014_jobs_request_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("book_size", sa.String(1), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "book_size")
