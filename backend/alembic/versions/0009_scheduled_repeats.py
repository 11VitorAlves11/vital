"""seasonality flag and scheduled repeats

Two related facts. `biomarkers.seasonal` says a marker's level genuinely moves
through the calendar year (vitamin D) — used only to say two draws far apart in
the year may differ partly because of when they were taken, never to guess a
direction, since the app has no hemisphere to reason from.

`scheduled_repeats` is a reminder to repeat one biomarker around a future
month, created from a result. Whether it is still pending is never stored —
derived at read time from whether a newer result exists — so the table carries
no status column, only the anchor (`source_collected_on`) that check needs.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import false

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "biomarkers",
        sa.Column("seasonal", sa.Boolean(), nullable=False, server_default=false()),
    )
    op.create_table(
        "scheduled_repeats",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "biomarker_id",
            sa.Integer(),
            sa.ForeignKey("biomarkers.id"),
            nullable=False,
        ),
        sa.Column(
            "source_result_id",
            sa.Uuid(),
            sa.ForeignKey("results.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_collected_on", sa.Date(), nullable=False),
        sa.Column("target_year", sa.SmallInteger(), nullable=False),
        sa.Column("target_month", sa.SmallInteger(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("target_month BETWEEN 1 AND 12", name="ck_scheduled_repeats_month"),
    )
    op.create_index("ix_scheduled_repeats_user_id", "scheduled_repeats", ["user_id"], unique=False)
    op.create_index(
        "ix_scheduled_repeats_biomarker_id", "scheduled_repeats", ["biomarker_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_scheduled_repeats_biomarker_id", table_name="scheduled_repeats")
    op.drop_index("ix_scheduled_repeats_user_id", table_name="scheduled_repeats")
    op.drop_table("scheduled_repeats")
    op.drop_column("biomarkers", "seasonal")
