"""project: tipo de capa soft ou hard

Revision ID: 0016_project_cover_type
Revises: 0015_project_book_size
Create Date: 2026-09-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016_project_cover_type"
down_revision: Union[str, None] = "0015_project_book_size"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("cover_type", sa.String(4), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "cover_type")
