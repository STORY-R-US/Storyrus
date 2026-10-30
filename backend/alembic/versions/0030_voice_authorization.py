"""Record the adult's explicit authorization for voice processing."""

import sqlalchemy as sa

from alembic import op

revision = "0030_voice_authorization"
down_revision = "0029_adult_confirmed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("processing_revoked_at", sa.DateTime(), nullable=True))
    op.add_column("projects", sa.Column("last_accessed_at", sa.DateTime(), nullable=True))
    op.add_column("user_voices", sa.Column("adult_authorization", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "last_accessed_at")
    op.drop_column("projects", "processing_revoked_at")
    op.drop_column("user_voices", "adult_authorization")
