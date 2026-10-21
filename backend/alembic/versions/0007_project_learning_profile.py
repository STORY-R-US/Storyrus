"""project: add child_trait and child_interest columns (perfil educativo da crianca)

Revision ID: 0007_project_learning_profile
Revises: 0006_project_extra_characters
Create Date: 2026-07-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_project_learning_profile"
down_revision: Union[str, None] = "0006_project_extra_characters"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("child_trait", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("child_interest", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "child_interest")
    op.drop_column("projects", "child_trait")
