"""progress photos

The v1.1 photo gallery. Stored dimensions come from the re-encoded image, not
from what the upload claimed: the file on disk is a fresh encode with no
metadata, so nothing about the camera or the place survives.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "progress_photos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("taken_on", sa.Date(), nullable=False),
        sa.Column(
            "pose",
            sa.Enum("frente", "lado", "costas", "outro", name="pose"),
            nullable=False,
        ),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
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
    op.create_index("ix_progress_photos_user_id", "progress_photos", ["user_id"])
    op.create_index("ix_progress_photos_taken_on", "progress_photos", ["taken_on"])


def downgrade() -> None:
    op.drop_index("ix_progress_photos_taken_on", table_name="progress_photos")
    op.drop_index("ix_progress_photos_user_id", table_name="progress_photos")
    op.drop_table("progress_photos")
    sa.Enum(name="pose").drop(op.get_bind(), checkfirst=True)
