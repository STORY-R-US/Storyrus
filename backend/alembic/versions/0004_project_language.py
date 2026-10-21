"""project: add language column (idioma do livro)

Revision ID: 0004_project_language
Revises: 0003_child_name_dedication
Create Date: 2026-07-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_project_language"
down_revision: Union[str, None] = "0003_child_name_dedication"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("language", sa.String(8), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "language")
