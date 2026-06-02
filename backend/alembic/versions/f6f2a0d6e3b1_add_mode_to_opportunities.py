"""add mode to opportunities

Revision ID: f6f2a0d6e3b1
Revises: db9306598689
Create Date: 2026-06-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f6f2a0d6e3b1"
down_revision: Union[str, None] = "db9306598689"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="rfp"),
    )


def downgrade() -> None:
    op.drop_column("opportunities", "mode")