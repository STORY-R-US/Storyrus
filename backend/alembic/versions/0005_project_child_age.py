"""project: add child_age column

Revision ID: 0005_project_child_age
Revises: 0004_project_language
Create Date: 2026-07-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_project_child_age"
down_revision: Union[str, None] = "0004_project_language"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("child_age", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "child_age")
