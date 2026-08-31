"""laboratories and doctors as entities, and notes at two levels

Backlog 1.7 and 1.8.

`lab_reports.lab_name` was free text, so two reports from the same laboratory
were the same place only by coincidence of spelling. It becomes a foreign key
into a per-account `labs` table, keyed on a normalised name so "Synlab Braga"
and "SYNLAB  braga" land on one row. Doctors get the same treatment, nullable,
because the ordering physician is rarely on the boletim.

Both tables are per-account rather than global: on a shared instance a global
list of laboratories would tell every account which ones the others use.

Notes gain a second level — one against the collection, one against a single
value — and a timestamp each, so an old reading is not mistaken for a current one.

The backfill runs in Python with its own copy of the normalisation, frozen at
what it meant here. Reimplementing it in SQL would risk producing keys the
application then fails to match, and every miss would be a duplicate laboratory.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-31
"""

import re
import unicodedata
import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def normalise(name: str) -> str:
    """A copy of app.services.text.normalise, as it stood at this revision."""
    folded = unicodedata.normalize("NFKD", name.casefold())
    folded = "".join(char for char in folded if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", folded).split())


def _backfill_labs() -> None:
    """One lab per distinct normalised name per account, under its first spelling."""
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, user_id, lab_name, created_at FROM lab_reports"
            " ORDER BY created_at, lab_name"
        )
    ).all()

    labs: dict[tuple[uuid.UUID, str], uuid.UUID] = {}
    for report_id, user_id, lab_name, created_at in rows:
        key = (user_id, normalise(lab_name))
        if key not in labs:
            labs[key] = uuid.uuid4()
            bind.execute(
                sa.text(
                    "INSERT INTO labs (id, user_id, name, normalised_name, created_at)"
                    " VALUES (:id, :user_id, :name, :normalised, :created_at)"
                ),
                {
                    "id": labs[key],
                    "user_id": user_id,
                    # The first spelling used, since the rows come in oldest first.
                    "name": lab_name.strip(),
                    "normalised": key[1],
                    "created_at": created_at,
                },
            )
        bind.execute(
            sa.text("UPDATE lab_reports SET lab_id = :lab_id WHERE id = :report_id"),
            {"lab_id": labs[key], "report_id": report_id},
        )


def upgrade() -> None:
    for table, extra in (("labs", []), ("doctors", [sa.Column("specialty", sa.String(120))])):
        op.create_table(
            table,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("normalised_name", sa.String(length=200), nullable=False),
            *extra,
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "normalised_name", name=f"uq_{table}_user_name"),
        )
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])

    op.add_column("lab_reports", sa.Column("lab_id", sa.Uuid(), nullable=True))
    op.add_column("lab_reports", sa.Column("doctor_id", sa.Uuid(), nullable=True))
    op.add_column("lab_reports", sa.Column("notes_at", sa.DateTime(timezone=True), nullable=True))

    _backfill_labs()

    op.alter_column("lab_reports", "lab_id", nullable=False)
    op.create_foreign_key(
        "fk_lab_reports_lab_id", "lab_reports", "labs", ["lab_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_foreign_key(
        "fk_lab_reports_doctor_id",
        "lab_reports",
        "doctors",
        ["doctor_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_lab_reports_lab_id", "lab_reports", ["lab_id"])
    op.create_index("ix_lab_reports_doctor_id", "lab_reports", ["doctor_id"])
    # A note that already exists was written at some point before now; the
    # report's own creation is the closest honest answer available.
    op.execute("UPDATE lab_reports SET notes_at = created_at WHERE notes IS NOT NULL")
    op.drop_column("lab_reports", "lab_name")

    op.add_column("results", sa.Column("note", sa.Text(), nullable=True))
    op.add_column("results", sa.Column("note_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("results", "note_at")
    op.drop_column("results", "note")

    op.add_column("lab_reports", sa.Column("lab_name", sa.String(), nullable=True))
    op.execute("UPDATE lab_reports SET lab_name = labs.name FROM labs WHERE labs.id = lab_id")
    op.alter_column("lab_reports", "lab_name", nullable=False)

    op.drop_index("ix_lab_reports_doctor_id", table_name="lab_reports")
    op.drop_index("ix_lab_reports_lab_id", table_name="lab_reports")
    op.drop_constraint("fk_lab_reports_doctor_id", "lab_reports", type_="foreignkey")
    op.drop_constraint("fk_lab_reports_lab_id", "lab_reports", type_="foreignkey")
    op.drop_column("lab_reports", "notes_at")
    op.drop_column("lab_reports", "doctor_id")
    op.drop_column("lab_reports", "lab_id")

    for table in ("doctors", "labs"):
        op.drop_index(f"ix_{table}_user_id", table_name=table)
        op.drop_table(table)
