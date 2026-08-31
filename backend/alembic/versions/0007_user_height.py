"""height on the profile

Height is what turns a weight into a BMI and a fat-free mass into an FFMI, and
those indices — not the raw kilograms — are where almost every body-composition
reference is defined. Nullable for the same reason as `sex`: without it the
derived indices are not computed at all, rather than computed against a guess.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("height_cm", sa.Numeric(4, 1), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "height_cm")
