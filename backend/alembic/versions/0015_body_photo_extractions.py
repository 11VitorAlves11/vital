"""Support photo extraction jobs for body composition.

Revision ID: 0015
Revises: 0014
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "extraction_jobs",
        sa.Column("kind", sa.String(length=20), server_default="lab", nullable=False),
    )
    op.add_column("extraction_jobs", sa.Column("body_scan_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_extraction_jobs_body_scan_id",
        "extraction_jobs",
        "body_scans",
        ["body_scan_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint("uq_extraction_user_hash", "extraction_jobs", type_="unique")
    op.create_unique_constraint(
        "uq_extraction_user_kind_hash",
        "extraction_jobs",
        ["user_id", "kind", "file_sha256"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_extraction_user_kind_hash", "extraction_jobs", type_="unique")
    op.create_unique_constraint(
        "uq_extraction_user_hash", "extraction_jobs", ["user_id", "file_sha256"]
    )
    op.drop_constraint("fk_extraction_jobs_body_scan_id", "extraction_jobs", type_="foreignkey")
    op.drop_column("extraction_jobs", "body_scan_id")
    op.drop_column("extraction_jobs", "kind")
