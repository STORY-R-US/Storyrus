"""project: add child_name and dedication columns

Revision ID: 0003_child_name_dedication
Revises: 0002_project_theme
Create Date: 2026-07-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_child_name_dedication"
down_revision: Union[str, None] = "0002_project_theme"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("child_name", sa.String(80), nullable=True))
    op.add_column("projects", sa.Column("dedication", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "dedication")
    op.drop_column("projects", "child_name")
