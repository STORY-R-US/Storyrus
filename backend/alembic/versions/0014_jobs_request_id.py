"""jobs: request_id for API ↔ worker correlation (STO-29)

Revision ID: 0014_jobs_request_id
Revises: 0013_jobs_status_created_idx
Create Date: 2026-09-17

Persiste o X-Request-ID da API no job para o worker reusar nos logs JSON
e na metadata do Opik.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_jobs_request_id"
down_revision: Union[str, None] = "0013_jobs_status_created_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("request_id", sa.String(length=128), nullable=True))
    op.create_index("ix_jobs_request_id", "jobs", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_jobs_request_id", table_name="jobs")
    op.drop_column("jobs", "request_id")
