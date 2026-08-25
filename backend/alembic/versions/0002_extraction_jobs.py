"""extraction jobs

The v1.1 PDF pipeline. A job holds the stored upload, the model that read it and
the answer that model gave, untouched — `results` is only ever written by the
confirm step, which a human has to trigger.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "extraction_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "processing",
                "preview",
                "confirmed",
                "failed",
                name="extraction_status",
            ),
            nullable=False,
        ),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("raw_output", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("report_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        # The report outlives the job it came from; deleting one must not take
        # the other's audit trail with it.
        sa.ForeignKeyConstraint(["report_id"], ["lab_reports.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_extraction_jobs_user_id", "extraction_jobs", ["user_id"])
    op.create_index("ix_extraction_jobs_status", "extraction_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_extraction_jobs_status", table_name="extraction_jobs")
    op.drop_index("ix_extraction_jobs_user_id", table_name="extraction_jobs")
    op.drop_table("extraction_jobs")
    sa.Enum(name="extraction_status").drop(op.get_bind(), checkfirst=True)
