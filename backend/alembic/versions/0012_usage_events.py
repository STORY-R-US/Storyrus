"""usage_events: uma linha por chamada de IA

Revision ID: 0012_usage_events
Revises: 0011_project_approvals_print
Create Date: 2026-09-03
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
from app.models import GUID, JSONType

revision: str = "0012_usage_events"
down_revision: Union[str, None] = "0011_project_approvals_print"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usage_events",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("job_id", GUID(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("meta", JSONType, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_usage_events_job_id", "usage_events", ["job_id"])
    op.create_index("ix_usage_events_project_id", "usage_events", ["project_id"])
    op.create_index("ix_usage_events_created_at", "usage_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_usage_events_created_at", table_name="usage_events")
    op.drop_index("ix_usage_events_project_id", table_name="usage_events")
    op.drop_index("ix_usage_events_job_id", table_name="usage_events")
    op.drop_table("usage_events")
