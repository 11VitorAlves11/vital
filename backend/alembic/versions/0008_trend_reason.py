"""why a body metric carries no clinical band

Sixteen of the twenty body metrics are trend-only, and the app said so with the
same four words on every card. The reason differs in every case — the weight is
read through the BMI, the bone mass is not something bioimpedance measures at
all — and the catalogue is where that reason belongs, beside the bands it
explains the absence of.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("body_metrics", sa.Column("trend_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("body_metrics", "trend_reason")
