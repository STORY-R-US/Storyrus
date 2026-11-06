"""Widen assets.kind so editorial_rejected fits.

The model already uses String(32). Production was still varchar(16) from the
initial migration, so saving a rejected preview crashed the EBOOK job.
"""

import sqlalchemy as sa

from alembic import op

revision = "0031_asset_kind_length"
down_revision = "0030_voice_authorization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("assets") as batch:
        batch.alter_column(
            "kind",
            existing_type=sa.String(16),
            type_=sa.String(32),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("assets") as batch:
        batch.alter_column(
            "kind",
            existing_type=sa.String(32),
            type_=sa.String(16),
            existing_nullable=False,
        )
