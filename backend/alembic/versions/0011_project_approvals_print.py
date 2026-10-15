"""project: avatar/book approval timestamps and print request

Revision ID: 0011_project_approvals_print
Revises: 0010_user_voices
Create Date: 2026-08-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_project_approvals_print"
down_revision: Union[str, None] = "0010_user_voices"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("character_approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("projects", sa.Column("book_approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("projects", sa.Column("print_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("projects", sa.Column("print_status", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "print_status")
    op.drop_column("projects", "print_requested_at")
    op.drop_column("projects", "book_approved_at")
    op.drop_column("projects", "character_approved_at")
