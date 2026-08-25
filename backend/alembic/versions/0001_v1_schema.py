"""v1 schema

Users, the shared catalogues (biomarkers, body metrics), lab reports with their
results, interventions and body scans. The v1.1 tables (`extraction_jobs`,
`progress_photos`) are deliberately absent until that pipeline is designed.

Revision ID: 0001
Revises:
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUM_TYPES = (
    "biomarker_category",
    "sex",
    "scan_source",
    "intervention_kind",
    "report_source",
    "result_flag",
)


def upgrade() -> None:
    op.create_table(
        "biomarkers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "hematologia",
                "bioquimica",
                "vitaminas",
                "ferro",
                "hormonas",
                "lipidos",
                "renal",
                "hepatico",
                "outro",
                name="biomarker_category",
            ),
            nullable=False,
        ),
        sa.Column("unit_default", sa.String(), nullable=False),
        sa.Column("ref_min_m", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("ref_max_m", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("ref_min_f", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("ref_max_f", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("aliases", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "body_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("unit", sa.String(), nullable=False),
        sa.Column("bands_m", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("bands_f", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("oidc_sub", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("sex", sa.Enum("M", "F", name="sex"), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("oidc_sub"),
    )
    op.create_table(
        "body_scans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.Enum("manual", "import", name="scan_source"), nullable=False),
        sa.Column("device", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_body_scans_user_id"), "body_scans", ["user_id"], unique=False)
    op.create_table(
        "interventions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "suplemento",
                "medicacao",
                "dieta",
                "treino",
                "outro",
                name="intervention_kind",
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("dose", sa.String(), nullable=True),
        sa.Column("started_on", sa.Date(), nullable=False),
        sa.Column("ended_on", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_interventions_user_id"), "interventions", ["user_id"], unique=False)
    op.create_table(
        "lab_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("collected_on", sa.Date(), nullable=False),
        sa.Column("lab_name", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("fasting", sa.Boolean(), nullable=True),
        sa.Column("source", sa.Enum("manual", "extracted", name="report_source"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lab_reports_user_id"), "lab_reports", ["user_id"], unique=False)
    op.create_table(
        "body_scan_values",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("metric_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("flag", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["metric_id"], ["body_metrics.id"]),
        sa.ForeignKeyConstraint(["scan_id"], ["body_scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scan_id", "metric_id", name="uq_scan_values_scan_metric"),
    )
    op.create_index(
        op.f("ix_body_scan_values_metric_id"), "body_scan_values", ["metric_id"], unique=False
    )
    op.create_index(
        op.f("ix_body_scan_values_scan_id"), "body_scan_values", ["scan_id"], unique=False
    )
    op.create_table(
        "results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("biomarker_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("unit", sa.String(), nullable=False),
        sa.Column("ref_min", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("ref_max", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("flag", sa.Enum("low", "normal", "high", name="result_flag"), nullable=True),
        sa.ForeignKeyConstraint(["biomarker_id"], ["biomarkers.id"]),
        sa.ForeignKeyConstraint(["report_id"], ["lab_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "biomarker_id", name="uq_results_report_marker"),
    )
    op.create_index(op.f("ix_results_biomarker_id"), "results", ["biomarker_id"], unique=False)
    op.create_index(op.f("ix_results_report_id"), "results", ["report_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_results_report_id"), table_name="results")
    op.drop_index(op.f("ix_results_biomarker_id"), table_name="results")
    op.drop_table("results")
    op.drop_index(op.f("ix_body_scan_values_scan_id"), table_name="body_scan_values")
    op.drop_index(op.f("ix_body_scan_values_metric_id"), table_name="body_scan_values")
    op.drop_table("body_scan_values")
    op.drop_index(op.f("ix_lab_reports_user_id"), table_name="lab_reports")
    op.drop_table("lab_reports")
    op.drop_index(op.f("ix_interventions_user_id"), table_name="interventions")
    op.drop_table("interventions")
    op.drop_index(op.f("ix_body_scans_user_id"), table_name="body_scans")
    op.drop_table("body_scans")
    op.drop_table("users")
    op.drop_table("body_metrics")
    op.drop_table("biomarkers")
    # Postgres keeps ENUM types after their tables are dropped.
    for enum_name in ENUM_TYPES:
        op.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name}"))
