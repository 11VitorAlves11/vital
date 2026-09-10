"""Add account-owned custom biomarkers.

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("biomarkers", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.create_index("ix_biomarkers_user_id", "biomarkers", ["user_id"])
    op.create_foreign_key(
        "fk_biomarkers_user_id",
        "biomarkers",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_biomarkers_user_id", "biomarkers", type_="foreignkey")
    op.drop_index("ix_biomarkers_user_id", table_name="biomarkers")
    op.drop_column("biomarkers", "user_id")
