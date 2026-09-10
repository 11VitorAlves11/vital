"""Add account and laboratory scoped biomarker match rules.

Revision ID: 0014
Revises: 0013
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "biomarker_match_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("biomarker_id", sa.Integer(), nullable=False),
        sa.Column("lab_name", sa.String(length=200), nullable=False),
        sa.Column("lab_name_normalised", sa.String(length=200), nullable=False),
        sa.Column("source_name", sa.String(length=200), nullable=False),
        sa.Column("source_name_normalised", sa.String(length=200), nullable=False),
        sa.Column("source_unit", sa.String(length=50), nullable=True),
        sa.Column("source_unit_normalised", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["biomarker_id"], ["biomarkers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "lab_name_normalised",
            "source_name_normalised",
            "source_unit_normalised",
            name="uq_biomarker_match_rules_source",
        ),
    )
    op.create_index("ix_biomarker_match_rules_user_id", "biomarker_match_rules", ["user_id"])
    op.create_index(
        "ix_biomarker_match_rules_biomarker_id", "biomarker_match_rules", ["biomarker_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_biomarker_match_rules_biomarker_id", table_name="biomarker_match_rules")
    op.drop_index("ix_biomarker_match_rules_user_id", table_name="biomarker_match_rules")
    op.drop_table("biomarker_match_rules")
