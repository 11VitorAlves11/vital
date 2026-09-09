"""hash and media type for extraction uploads

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("extraction_jobs", sa.Column("file_sha256", sa.String(length=64)))
    op.add_column(
        "extraction_jobs",
        sa.Column(
            "media_type",
            sa.String(length=50),
            nullable=False,
            server_default="application/pdf",
        ),
    )
    op.create_index("ix_extraction_jobs_file_sha256", "extraction_jobs", ["file_sha256"])
    op.create_unique_constraint(
        "uq_extraction_user_hash", "extraction_jobs", ["user_id", "file_sha256"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_extraction_user_hash", "extraction_jobs", type_="unique")
    op.drop_index("ix_extraction_jobs_file_sha256", table_name="extraction_jobs")
    op.drop_column("extraction_jobs", "media_type")
    op.drop_column("extraction_jobs", "file_sha256")
