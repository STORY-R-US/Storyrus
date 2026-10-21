"""project: add extra_theme column (segundo tema opcional combinado na historia)

Revision ID: 0008_project_extra_theme
Revises: 0007_project_learning_profile
Create Date: 2026-07-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_project_extra_theme"
down_revision: Union[str, None] = "0007_project_learning_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("extra_theme", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "extra_theme")
