"""print_orders: pedido do livro impresso, separado do resumo da foto

Revision ID: 0018_print_orders
Revises: 0017_order_tickets
Create Date: 2026-10-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models import GUID, JSONType

revision: str = "0018_print_orders"
down_revision: Union[str, None] = "0017_order_tickets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "print_orders",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "project_id",
            GUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("book_size", sa.String(1), nullable=True),
        sa.Column("cover_type", sa.String(8), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(32), nullable=False, server_default="awaiting_spec"),
        sa.Column("block_reason", sa.Text(), nullable=True),
        sa.Column("cover_key", sa.Text(), nullable=True),
        sa.Column("interior_key", sa.Text(), nullable=True),
        sa.Column("recipient_name", sa.String(120), nullable=True),
        sa.Column("postal_code", sa.String(16), nullable=True),
        sa.Column("street", sa.String(160), nullable=True),
        sa.Column("number", sa.String(20), nullable=True),
        sa.Column("complement", sa.String(80), nullable=True),
        sa.Column("district", sa.String(80), nullable=True),
        sa.Column("city", sa.String(80), nullable=True),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("freight_options", JSONType, nullable=True),
        sa.Column("freight_service_id", sa.Integer(), nullable=True),
        sa.Column("freight_service_name", sa.String(80), nullable=True),
        sa.Column("freight_price_cents", sa.Integer(), nullable=True),
        sa.Column("freight_days", sa.Integer(), nullable=True),
        sa.Column("payment_status", sa.String(16), nullable=False, server_default="unpaid"),
        sa.Column("payment_provider", sa.String(32), nullable=True),
        sa.Column("payment_reference", sa.String(80), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=True),
        sa.Column("tracking_code", sa.String(64), nullable=True),
        sa.Column("label_url", sa.Text(), nullable=True),
        sa.Column("label_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", name="uq_print_orders_project_id"),
        sa.UniqueConstraint("code", name="uq_print_orders_code"),
    )


def downgrade() -> None:
    op.drop_table("print_orders")
