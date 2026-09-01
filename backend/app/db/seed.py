"""Load the shared clinical catalogues into the database.

Idempotent upsert keyed on `slug`: the JSON files in seed/ are the source of truth,
so editing a band there and restarting is enough to correct every future flag —
without renumbering ids that results already point at.
"""

import asyncio
import json
from datetime import time
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import dispose_engine, get_sessionmaker
from app.models import Biomarker, BodyMetric
from app.models.enums import ReferenceKind
from app.services.recompute import recompute_every_users_flags

BIOMARKER_FIELDS = (
    "slug",
    "name",
    "category",
    "unit_default",
    "canonical_unit",
    "unit_conversions",
    "reference_kind",
    "ref_min_m",
    "ref_max_m",
    "ref_min_f",
    "ref_max_f",
    "ordinal_bands",
    "fasting_sensitive",
    "fasting_min_hours",
    "time_sensitive",
    "time_window_start",
    "time_window_end",
    "low_reliability_methods",
    "aliases",
    "notes",
)
BODY_METRIC_FIELDS = (
    "slug",
    "name",
    "unit",
    "bands_m",
    "bands_f",
    "source",
    "trend_reason",
    "notes",
)
DECIMAL_FIELDS = frozenset({"ref_min_m", "ref_max_m", "ref_min_f", "ref_max_f"})
TIME_FIELDS = frozenset({"time_window_start", "time_window_end"})
#: Columns the JSON may leave out, with what "left out" means for each.
DEFAULTS: dict[str, Any] = {
    "unit_conversions": {},
    "reference_kind": ReferenceKind.TWO_SIDED.value,
    "fasting_sensitive": False,
    "time_sensitive": False,
    "low_reliability_methods": [],
}


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
    for field in TIME_FIELDS & row.keys():
        written = row[field]
        if written is not None:
            row[field] = time.fromisoformat(str(written))
    # The common case is a marker reported in one unit, on a two-sided range,
    # that nothing about the collection disturbs — so the entries that are only
    # that say nothing about any of it.
    if "canonical_unit" in row and row["canonical_unit"] is None:
        row["canonical_unit"] = entry["unit_default"]
    for field, default in DEFAULTS.items():
        if field in row and row[field] is None:
            row[field] = default
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
        accounts = await recompute_every_users_flags(db)
    await dispose_engine()
    print(
        f"Catálogo carregado: {biomarkers} biomarcadores, {body_metrics} métricas corporais. "
        f"{accounts} conta(s) reclassificada(s)."
    )


if __name__ == "__main__":
    asyncio.run(main())
