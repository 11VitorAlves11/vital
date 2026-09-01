"""The seed loader: the catalogue in the database must equal the catalogue in seed/."""

import json
from decimal import Decimal

from sqlalchemy import func, select

from app.db.seed import load_catalogue, seed_dir
from app.db.session import get_sessionmaker
from app.models import Biomarker, BodyMetric


def _seed(name: str) -> list[dict[str, object]]:
    return json.loads((seed_dir() / name).read_text(encoding="utf-8"))


async def test_row_counts_match_the_json_exactly(database: None) -> None:
    biomarkers = _seed("biomarkers.json")
    body_metrics = _seed("body_metrics.json")
    async with get_sessionmaker()() as db:
        assert await db.scalar(select(func.count()).select_from(Biomarker)) == len(biomarkers)
        assert await db.scalar(select(func.count()).select_from(BodyMetric)) == len(body_metrics)
    # A floor, not a census: the assertions above already tie the tables to the
    # JSON exactly. This one only catches the file being truncated or emptied,
    # which an exact count would too — at the price of a test edit every time
    # the catalogue legitimately grows.
    assert len(biomarkers) >= 31
    assert len(body_metrics) >= 18


async def test_loading_twice_inserts_nothing_new(database: None) -> None:
    async with get_sessionmaker()() as db:
        before = await db.scalar(select(func.count()).select_from(Biomarker))
        await load_catalogue(db)
        await load_catalogue(db)
        after = await db.scalar(select(func.count()).select_from(Biomarker))
    assert before == after


async def test_reloading_keeps_the_ids_results_point_at(database: None) -> None:
    """Ids are foreign keys from every stored result — a reload must not renumber them."""
    async with get_sessionmaker()() as db:
        before = {row.slug: row.id for row in (await db.execute(select(Biomarker))).scalars().all()}
        await load_catalogue(db)
        after = {row.slug: row.id for row in (await db.execute(select(Biomarker))).scalars().all()}
    assert before == after


async def test_canonical_ranges_round_trip_unmodified(database: None) -> None:
    entries = {entry["slug"]: entry for entry in _seed("biomarkers.json")}
    async with get_sessionmaker()() as db:
        rows = (await db.execute(select(Biomarker))).scalars().all()

    for row in rows:
        entry = entries[row.slug]
        for field in ("ref_min_m", "ref_max_m", "ref_min_f", "ref_max_f"):
            expected = entry[field]
            stored = getattr(row, field)
            if expected is None:
                assert stored is None, (row.slug, field)
            else:
                assert stored == Decimal(str(expected)), (row.slug, field)
        assert row.aliases == entry["aliases"]
        assert row.category.value == entry["category"]
        assert row.unit_default == entry["unit_default"]


async def test_bands_round_trip_unmodified(database: None) -> None:
    entries = {entry["slug"]: entry for entry in _seed("body_metrics.json")}
    async with get_sessionmaker()() as db:
        rows = (await db.execute(select(BodyMetric))).scalars().all()

    for row in rows:
        entry = entries[row.slug]
        assert row.bands_m == entry["bands_m"], row.slug
        assert row.bands_f == entry["bands_f"], row.slug
        assert row.source == entry["source"], row.slug
        assert row.trend_reason == entry["trend_reason"], row.slug


async def test_every_metric_that_cannot_flag_says_why(database: None) -> None:
    """The card shows this sentence where a classified metric shows its standard.

    Without it the page falls back to the same four words on every unclassified
    metric, which is what it said before and told the reader nothing.
    """
    async with get_sessionmaker()() as db:
        rows = (await db.execute(select(BodyMetric))).scalars().all()

    for row in rows:
        classifies = row.bands_m is not None and any(
            band.get("flag") is not None for band in row.bands_m
        )
        assert bool(row.trend_reason) is not classifies, row.slug


async def test_trend_only_metrics_are_sql_null_not_json_null(database: None) -> None:
    """`bands_m IS NULL` has to mean 'no clinical standard', so it must be queryable."""
    async with get_sessionmaker()() as db:
        trend_only = (
            (await db.execute(select(BodyMetric).where(BodyMetric.bands_m.is_(None))))
            .scalars()
            .all()
        )
    entries = _seed("body_metrics.json")
    expected = {entry["slug"] for entry in entries if entry["bands_m"] is None}
    banded = {entry["slug"] for entry in entries if entry["bands_m"] is not None}
    assert {row.slug for row in trend_only} == expected
    # Both directions, rather than a count that goes stale every time the
    # catalogue grows: nothing banded may be NULL, and something must be banded.
    assert expected and banded
    assert not (banded & {row.slug for row in trend_only})
