"""order_tickets: pedido criado quando a foto do livro é recebida

Revision ID: 0017_order_tickets
Revises: 0016_project_cover_type
Create Date: 2026-09-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models import GUID

revision: str = "0017_order_tickets"
down_revision: Union[str, None] = "0016_project_cover_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "order_tickets",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "project_id",
            GUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", name="uq_order_tickets_project_id"),
    )
    op.create_index("ix_order_tickets_created_at", "order_tickets", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_order_tickets_created_at", table_name="order_tickets")
    op.drop_table("order_tickets")
