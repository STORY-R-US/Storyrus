"""project: add theme column

Revision ID: 0002_project_theme
Revises: 0001_init
Create Date: 2026-06-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_project_theme"
down_revision: Union[str, None] = "0001_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("theme", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "theme")
