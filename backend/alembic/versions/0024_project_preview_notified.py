"""project: avisa o cliente quando a previa fica pronta

Revision ID: 0024_project_preview_notified
Revises: 0023_user_is_admin
Create Date: 2026-10-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0024_project_preview_notified"
down_revision: Union[str, None] = "0023_user_is_admin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("preview_notified_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "preview_notified_at")
