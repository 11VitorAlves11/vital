"""Add per-user model settings.

Revision ID: 0012
Revises: 0011
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("llm_model", sa.String(length=300), nullable=True))
    op.add_column("users", sa.Column("llm_base_url", sa.String(length=500), nullable=True))
    op.add_column("users", sa.Column("llm_api_key_encrypted", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "llm_api_key_encrypted")
    op.drop_column("users", "llm_base_url")
    op.drop_column("users", "llm_model")
