"""jobs: composite index (status, created_at) for queue claim

Revision ID: 0013_jobs_status_created_idx
Revises: 0012_usage_events
Create Date: 2026-09-17

STO-30: claim_next filtra por status e ordena por created_at ASC.
O indice simples ix_jobs_status nao cobre o ORDER BY; o composto
(status, created_at) cobre o padrao WHERE status = ? ORDER BY created_at
e tambem lookups so por status (prefixo esquerdo).

Note: revision id kept <= 32 chars (alembic_version.version_num default).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0013_jobs_status_created_idx"
down_revision: Union[str, None] = "0012_usage_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_jobs_status_created_at", "jobs", ["status", "created_at"])
    op.drop_index("ix_jobs_status", table_name="jobs")


def downgrade() -> None:
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.drop_index("ix_jobs_status_created_at", table_name="jobs")
