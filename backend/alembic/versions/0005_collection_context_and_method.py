"""collection context and analytical method

Backlog 1.4 and 1.5. What was around the draw, and what measured it.

`fasting` was a nullable boolean, which conflated "they had eaten" with "nobody
wrote it down" — the second is worth prompting about and the first is not. It
becomes a three-state enum, and gains the hours behind it. `collected_at` adds
the hour of the draw, without a zone: the diurnal variation this exists to catch
is at a local hour, and no report ever states an offset.

`results.method` records the assay. Two laboratories measuring the same blood by
different methods can differ by more than the change being watched for, so
comparing across a change of method needs the change to be visible.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FASTING_STATE = sa.Enum("fasting", "not_fasting", "unknown", name="fasting_state")


def upgrade() -> None:
    FASTING_STATE.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "biomarkers",
        sa.Column("fasting_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("biomarkers", sa.Column("fasting_min_hours", sa.SmallInteger(), nullable=True))
    op.add_column(
        "biomarkers",
        sa.Column("time_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("biomarkers", sa.Column("time_window_start", sa.Time(), nullable=True))
    op.add_column("biomarkers", sa.Column("time_window_end", sa.Time(), nullable=True))
    op.add_column(
        "biomarkers",
        sa.Column(
            "low_reliability_methods",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )

    op.add_column(
        "lab_reports", sa.Column("collected_at", sa.DateTime(timezone=False), nullable=True)
    )
    op.add_column("lab_reports", sa.Column("fasting_hours", sa.SmallInteger(), nullable=True))
    op.add_column(
        "lab_reports",
        sa.Column("fasting_state", FASTING_STATE, nullable=False, server_default="unknown"),
    )
    # NULL was "nobody said", true and false were the two answers — which is
    # exactly the three states, so nothing is lost or invented in the move.
    op.execute(
        """
        UPDATE lab_reports SET fasting_state = CASE
            WHEN fasting IS TRUE THEN 'fasting'
            WHEN fasting IS FALSE THEN 'not_fasting'
            ELSE 'unknown'
        END::fasting_state
        """
    )
    op.drop_column("lab_reports", "fasting")

    op.add_column("results", sa.Column("method", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("results", "method")

    op.add_column("lab_reports", sa.Column("fasting", sa.Boolean(), nullable=True))
    op.execute(
        """
        UPDATE lab_reports SET fasting = CASE
            WHEN fasting_state = 'fasting' THEN TRUE
            WHEN fasting_state = 'not_fasting' THEN FALSE
        END
        """
    )
    op.drop_column("lab_reports", "fasting_state")
    op.drop_column("lab_reports", "fasting_hours")
    op.drop_column("lab_reports", "collected_at")

    op.drop_column("biomarkers", "low_reliability_methods")
    op.drop_column("biomarkers", "time_window_end")
    op.drop_column("biomarkers", "time_window_start")
    op.drop_column("biomarkers", "time_sensitive")
    op.drop_column("biomarkers", "fasting_min_hours")
    op.drop_column("biomarkers", "fasting_sensitive")

    FASTING_STATE.drop(op.get_bind(), checkfirst=True)
