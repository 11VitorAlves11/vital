"""reference kinds and canonical units

Backlog 1.2 and 1.3. Two things a v1 result could not express: that an interval
is a single bound or a named scale rather than two numbers, and that the same
marker arrives in different units from different laboratories.

Existing rows are backfilled rather than left null. Their reference kind is
inferred from the bounds already stored, and their canonical value from the unit
already stored — both of which are exactly what the application would derive for
them today. `python -m app.db.seed` afterwards fills the catalogue's own
conversion tables and ordinal bands.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REFERENCE_KIND = sa.Enum(
    "two_sided",
    "upper_bound",
    "lower_bound",
    "ordinal_bands",
    "none",
    name="reference_kind",
)

#: The bounds a row already has decide the shape it has always had.
SHAPE_OF = """
    CASE
        WHEN {minimum} IS NOT NULL AND {maximum} IS NOT NULL THEN 'two_sided'
        WHEN {maximum} IS NOT NULL THEN 'upper_bound'
        WHEN {minimum} IS NOT NULL THEN 'lower_bound'
        ELSE 'none'
    END::reference_kind
"""

BACKFILL_BIOMARKERS = "UPDATE biomarkers SET reference_kind = " + SHAPE_OF.format(
    minimum="COALESCE(ref_min_m, ref_min_f)", maximum="COALESCE(ref_max_m, ref_max_f)"
)

#: The catalogue's own bound for the account that owns the result, or NULL.
CATALOGUE_BOUND = (
    "(CASE users.sex WHEN 'F' THEN biomarkers.{limit}_f ELSE biomarkers.{limit}_m END)"
)

# The interval a result was read against is the lab's when the lab printed one,
# and otherwise the catalogue's for that account's sex — which is what the
# application derives today, so the backfill derives the same thing. A one-sided
# lab range is never topped up from the catalogue, hence the outer CASE on
# "did the lab print anything at all" rather than a COALESCE per bound.
BACKFILL_RESULTS = f"""
    UPDATE results SET reference_kind = CASE
        WHEN results.ref_min IS NOT NULL OR results.ref_max IS NOT NULL
            THEN {SHAPE_OF.format(minimum="results.ref_min", maximum="results.ref_max")}
        WHEN users.sex IS NULL THEN 'none'::reference_kind
        ELSE {
    SHAPE_OF.format(
        minimum=CATALOGUE_BOUND.format(limit="ref_min"),
        maximum=CATALOGUE_BOUND.format(limit="ref_max"),
    )
}
    END
    FROM lab_reports, users, biomarkers
    WHERE lab_reports.id = results.report_id
      AND users.id = lab_reports.user_id
      AND biomarkers.id = results.biomarker_id
"""


def upgrade() -> None:
    bind = op.get_bind()
    REFERENCE_KIND.create(bind, checkfirst=True)

    op.add_column("biomarkers", sa.Column("canonical_unit", sa.String(), nullable=True))
    op.add_column(
        "biomarkers",
        sa.Column(
            "unit_conversions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "biomarkers",
        sa.Column("reference_kind", REFERENCE_KIND, nullable=False, server_default="two_sided"),
    )
    op.add_column(
        "biomarkers",
        sa.Column("ordinal_bands", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    # Before the catalogue is reseeded, a marker is canonical in the unit it
    # already defaults to — which is what every stored result is already in.
    op.execute("UPDATE biomarkers SET canonical_unit = unit_default")
    op.alter_column("biomarkers", "canonical_unit", nullable=False)
    op.execute(BACKFILL_BIOMARKERS)

    op.add_column("results", sa.Column("canonical_value", sa.Numeric(12, 4), nullable=True))
    op.add_column("results", sa.Column("canonical_unit", sa.String(), nullable=True))
    op.add_column("results", sa.Column("conversion_factor", sa.Numeric(12, 4), nullable=True))
    op.add_column(
        "results",
        sa.Column("reference_kind", REFERENCE_KIND, nullable=False, server_default="none"),
    )
    op.add_column(
        "results",
        sa.Column("reference_bands", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    # Every existing result is in its own marker's canonical unit by definition
    # of the line above, so the conversion is the identity — recorded, not left
    # null, so "converted with factor 1" and "not convertible" stay distinct.
    op.execute(
        """
        UPDATE results SET
            canonical_value = results.value,
            canonical_unit = biomarkers.canonical_unit,
            conversion_factor = 1
        FROM biomarkers
        WHERE biomarkers.id = results.biomarker_id
        """
    )
    op.execute(BACKFILL_RESULTS)


def downgrade() -> None:
    op.drop_column("results", "reference_bands")
    op.drop_column("results", "reference_kind")
    op.drop_column("results", "conversion_factor")
    op.drop_column("results", "canonical_unit")
    op.drop_column("results", "canonical_value")
    op.drop_column("biomarkers", "ordinal_bands")
    op.drop_column("biomarkers", "reference_kind")
    op.drop_column("biomarkers", "unit_conversions")
    op.drop_column("biomarkers", "canonical_unit")
    REFERENCE_KIND.drop(op.get_bind(), checkfirst=True)
