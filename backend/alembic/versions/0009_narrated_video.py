"""project: narrated_video_url

Revision ID: 0009_narrated_video
Revises: 0008_project_extra_theme
Create Date: 2026-07-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_narrated_video"
down_revision: Union[str, None] = "0008_project_extra_theme"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("narrated_video_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "narrated_video_url")
