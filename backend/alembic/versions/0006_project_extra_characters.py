"""project: add extra_characters column

Revision ID: 0006_project_extra_characters
Revises: 0005_project_child_age
Create Date: 2026-07-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_project_extra_characters"
down_revision: Union[str, None] = "0005_project_child_age"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("extra_characters", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "extra_characters")
