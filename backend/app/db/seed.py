"""Load the shared clinical catalogues into the database.

Idempotent upsert keyed on `slug`: the JSON files in seed/ are the source of truth,
so editing a band there and restarting is enough to correct every future flag —
without renumbering ids that results already point at.
"""

import asyncio
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import dispose_engine, get_sessionmaker
from app.models import Biomarker, BodyMetric

BIOMARKER_FIELDS = (
    "slug",
    "name",
    "category",
    "unit_default",
    "ref_min_m",
    "ref_max_m",
    "ref_min_f",
    "ref_max_f",
    "aliases",
    "notes",
)
BODY_METRIC_FIELDS = ("slug", "name", "unit", "bands_m", "bands_f", "source", "notes")
DECIMAL_FIELDS = frozenset({"ref_min_m", "ref_max_m", "ref_min_f", "ref_max_f"})


def seed_dir() -> Path:
    """Locate seed/ next to the app (Docker) or at the repo root (local checkout)."""
    here = Path(__file__).resolve()
    for candidate in (here.parents[2] / "seed", here.parents[3] / "seed"):
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("seed/ not found — expected next to the app or at the repo root")


def _read(name: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = json.loads((seed_dir() / name).read_text(encoding="utf-8"))
    return entries


def _row(entry: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    row = {field: entry.get(field) for field in fields}
    for field in DECIMAL_FIELDS & row.keys():
        if row[field] is not None:
            # Through str, so 0.1 stays 0.1 instead of the nearest binary float.
            row[field] = Decimal(str(row[field]))
    return row


async def _upsert(
    db: AsyncSession, model: type[Biomarker] | type[BodyMetric], rows: list[dict[str, Any]]
) -> int:
    if not rows:
        return 0
    statement = insert(model).values(rows)
    updatable = {key: statement.excluded[key] for key in rows[0] if key != "slug"}
    await db.execute(statement.on_conflict_do_update(index_elements=["slug"], set_=updatable))
    return len(rows)


async def load_catalogue(db: AsyncSession) -> tuple[int, int]:
    """Upsert both catalogues; returns (biomarkers, body metrics) written."""
    biomarkers = [_row(entry, BIOMARKER_FIELDS) for entry in _read("biomarkers.json")]
    body_metrics = [_row(entry, BODY_METRIC_FIELDS) for entry in _read("body_metrics.json")]
    written = (
        await _upsert(db, Biomarker, biomarkers),
        await _upsert(db, BodyMetric, body_metrics),
    )
    await db.commit()
    return written


async def main() -> None:
    async with get_sessionmaker()() as db:
        biomarkers, body_metrics = await load_catalogue(db)
    await dispose_engine()
    print(f"Catálogo carregado: {biomarkers} biomarcadores, {body_metrics} métricas corporais.")


if __name__ == "__main__":
    asyncio.run(main())
