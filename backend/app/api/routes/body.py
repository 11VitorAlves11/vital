"""Body composition — weigh-ins and their clinically classified values."""

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, time
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.api.routes.catalog import to_body_metric_out
from app.models import BodyMetric, BodyScan, BodyScanValue, User
from app.models.enums import ScanSource
from app.schemas.body import (
    BodyMetricSummary,
    BodyScanCreate,
    BodyScanOut,
    BodySparkPoint,
    ScanValueOut,
)
from app.schemas.dashboard import SPARKLINE_POINTS
from app.schemas.interventions import InterventionOut
from app.schemas.series import BodyPoint, BodySeries
from app.services import anthropometrics
from app.services.bands import bands_for, classify
from app.services.overlay import overlapping_interventions

router = APIRouter(prefix="/body", tags=["body"])


def to_value_out(value: BodyScanValue, user: User) -> ScanValueOut:
    """The stored flag is authoritative; the band label is looked up for display,
    because a colour on its own is not a signal."""
    _, label = classify(value.value, bands_for(value.metric, user.sex))
    return ScanValueOut(
        id=value.id,
        metric_id=value.metric_id,
        metric_slug=value.metric.slug,
        metric_name=value.metric.name,
        unit=value.metric.unit,
        value=value.value,
        flag=value.flag,  # type: ignore[arg-type]
        label=label,
    )


def derived_values(
    scan: BodyScan, user: User, catalogue: dict[str, BodyMetric]
) -> list[ScanValueOut]:
    """The indices height makes computable, classified like any other value.

    Computed on read: a stored one would need chasing down every time someone
    corrected their height, and would sit in the measurements table looking
    exactly like a measurement.
    """
    measured = {value.metric.slug: value.value for value in scan.values}
    out: list[ScanValueOut] = []
    for item in anthropometrics.derive(measured, user.height_cm):
        metric = catalogue.get(item.metric_slug)
        if metric is None:
            continue
        flag, label = classify(item.value, bands_for(metric, user.sex))
        out.append(
            ScanValueOut(
                metric_id=metric.id,
                metric_slug=metric.slug,
                metric_name=metric.name,
                unit=metric.unit,
                value=item.value,
                flag=flag,  # type: ignore[arg-type]
                label=label,
                derived_from=item.source_slug,
            )
        )
    return out


async def metric_catalogue(db: DbSession) -> dict[str, BodyMetric]:
    metrics = (await db.execute(select(BodyMetric))).scalars().all()
    return {metric.slug: metric for metric in metrics}


def to_scan_out(scan: BodyScan, user: User, catalogue: dict[str, BodyMetric]) -> BodyScanOut:
    return BodyScanOut(
        id=scan.id,
        measured_at=scan.measured_at,
        source=scan.source,
        device=scan.device,
        notes=scan.notes,
        values=[to_value_out(value, user) for value in scan.values]
        + derived_values(scan, user, catalogue),
    )


@router.get("/scans", response_model=list[BodyScanOut])
async def list_scans(
    user: CurrentUser,
    db: DbSession,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
) -> list[BodyScanOut]:
    statement = (
        select(BodyScan).where(BodyScan.user_id == user.id).order_by(BodyScan.measured_at.desc())
    )
    if date_from is not None:
        statement = statement.where(
            BodyScan.measured_at >= datetime.combine(date_from, time.min, tzinfo=UTC)
        )
    if date_to is not None:
        statement = statement.where(
            BodyScan.measured_at <= datetime.combine(date_to, time.max, tzinfo=UTC)
        )
    scans = (await db.execute(statement)).scalars().all()
    metrics = await metric_catalogue(db)
    return [to_scan_out(scan, user, metrics) for scan in scans]


@router.post("/scans", response_model=BodyScanOut, status_code=status.HTTP_201_CREATED)
async def create_scan(payload: BodyScanCreate, user: CurrentUser, db: DbSession) -> BodyScanOut:
    """Record a weigh-in. Every flag is recomputed from the clinical bands here —
    whatever rating the scale printed is discarded."""
    requested = [value.metric_id for value in payload.values]
    catalogue = {
        metric.id: metric
        for metric in (
            (await db.execute(select(BodyMetric).where(BodyMetric.id.in_(requested))))
            .scalars()
            .all()
        )
    }
    unknown = sorted(set(requested) - catalogue.keys())
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown body metric ids: {unknown}",
        )

    scan = BodyScan(
        user_id=user.id,
        measured_at=payload.measured_at,
        device=payload.device,
        notes=payload.notes,
        source=ScanSource.MANUAL,
    )
    for entry in payload.values:
        metric = catalogue[entry.metric_id]
        flag, _ = classify(entry.value, bands_for(metric, user.sex))
        scan.values.append(BodyScanValue(metric_id=metric.id, value=entry.value, flag=flag))

    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return to_scan_out(scan, user, await metric_catalogue(db))


async def _readings(
    user: User, db: DbSession, metrics: dict[str, BodyMetric]
) -> list[tuple[datetime, list[ScanValueOut]]]:
    """Every weigh-in oldest first, each with its measured and derived values.

    Grouped by scan rather than by metric because a derived index is a fact
    about one weigh-in: it needs that weigh-in's other values to exist at all.
    """
    statement = select(BodyScan).where(BodyScan.user_id == user.id).order_by(BodyScan.measured_at)
    scans = (await db.execute(statement)).scalars().all()
    return [
        (
            scan.measured_at,
            [to_value_out(value, user) for value in scan.values]
            + derived_values(scan, user, metrics),
        )
        for scan in scans
    ]


@router.get("/metrics/{metric_id}/series", response_model=BodySeries)
async def metric_series(metric_id: int, user: CurrentUser, db: DbSession) -> BodySeries:
    """One metric across every weigh-in, oldest first, with the intervention overlay."""
    metric = await db.get(BodyMetric, metric_id)
    if metric is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Body metric not found")

    readings = await _readings(user, db, await metric_catalogue(db))
    points = [
        BodyPoint(
            date=measured_at,
            value=value.value,
            flag=value.flag,
            label=value.label,
            scan_id=str(value.id) if value.id else "",
        )
        for measured_at, values in readings
        for value in values
        if value.metric_id == metric_id
    ]
    interventions = await overlapping_interventions(
        db,
        user.id,
        points[0].date.date() if points else None,
        points[-1].date.date() if points else None,
    )
    return BodySeries(
        metric=to_body_metric_out(metric, user),
        points=points,
        interventions=[InterventionOut.model_validate(item) for item in interventions],
    )


@router.get("/summary", response_model=list[BodyMetricSummary])
async def body_summary(user: CurrentUser, db: DbSession) -> list[BodyMetricSummary]:
    """The metrics grid: latest reading, its clinical band, and a short sparkline."""
    catalogue = await metric_catalogue(db)
    readings = await _readings(user, db, catalogue)

    history: dict[int, list[tuple[datetime, ScanValueOut]]] = defaultdict(list)
    for measured_at, values in readings:
        for value in values:
            history[value.metric_id].append((measured_at, value))

    metrics = (await db.execute(select(BodyMetric).order_by(BodyMetric.id))).scalars().all()
    summaries: list[BodyMetricSummary] = []
    for metric in metrics:
        entries = history.get(metric.id)
        if not entries:
            continue
        measured_at, latest = entries[-1]
        summaries.append(
            BodyMetricSummary(
                metric=to_body_metric_out(metric, user),
                latest=latest,
                measured_at=measured_at,
                sparkline=[
                    BodySparkPoint(date=moment, value=value.value)
                    for moment, value in entries[-SPARKLINE_POINTS:]
                ],
            )
        )
    return summaries


@router.delete("/scans/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scan(scan_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    statement = select(BodyScan).where(BodyScan.id == scan_id, BodyScan.user_id == user.id)
    scan = (await db.execute(statement)).scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    await db.delete(scan)
    await db.commit()
