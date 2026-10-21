"""user_voices table

Revision ID: 0010_user_voices
Revises: 0009_narrated_video
Create Date: 2026-07-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models import GUID

revision: str = "0010_user_voices"
down_revision: Union[str, None] = "0009_narrated_video"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_voices",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("elevenlabs_voice_id", sa.String(64), nullable=False),
        sa.Column("sample_storage_key", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False, server_default="audio/mpeg"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_user_voices_user_id", "user_voices", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_voices_user_id", table_name="user_voices")
    op.drop_table("user_voices")
