"""age-partitioned bands for body fat percentage

Backlog 5.3. `bands_m`/`bands_f` classify a value against one interval for
someone's whole adult life; body-fat-pct is where that stops being true — the
same reading means something different at 25 and at 65. `age_bands_m`/`_f`
add a second, age-partitioned layer of the same band shape, read against age
at the date of measurement rather than today's.

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("body_metrics", sa.Column("age_bands_m", JSONB(none_as_null=True)))
    op.add_column("body_metrics", sa.Column("age_bands_f", JSONB(none_as_null=True)))


def downgrade() -> None:
    op.drop_column("body_metrics", "age_bands_f")
    op.drop_column("body_metrics", "age_bands_m")
