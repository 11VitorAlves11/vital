"""The shared catalogues: biomarkers and body-composition metrics.

Both are global, but what a caller sees is not: reference ranges and clinical bands
are resolved for their sex before leaving the server, so no client ever has to pick.
"""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select

from app.api.deps import CurrentUser, DbSession
from app.models import Biomarker, BodyMetric, LabReport, Result, User
from app.models.enums import BiomarkerCategory, ReferenceKind
from app.schemas.catalog import (
    BandOut,
    BiomarkerOut,
    BodyMetricOut,
    CustomBiomarkerCreate,
    ReferenceBandOut,
)
from app.schemas.interventions import InterventionOut
from app.schemas.reports import CaveatOut
from app.schemas.series import BiomarkerPoint, BiomarkerSeries
from app.services import caveats, timeline
from app.services.bands import bands_for
from app.services.flags import Reference, band_label, canonical_reference
from app.services.overlay import overlapping_interventions
from app.services.units import convert_bound

router = APIRouter(tags=["catalogue"])


def to_biomarker_out(biomarker: Biomarker, user: User) -> BiomarkerOut:
    reference = canonical_reference(biomarker, user.sex)
    return BiomarkerOut(
        id=biomarker.id,
        slug=biomarker.slug,
        name=biomarker.name,
        category=biomarker.category,
        unit_default=biomarker.unit_default,
        canonical_unit=biomarker.canonical_unit,
        reference_kind=reference.kind,
        ref_min=reference.minimum,
        ref_max=reference.maximum,
        reference_bands=(
            [ReferenceBandOut.model_validate(band) for band in reference.bands]
            if reference.bands
            else None
        ),
        aliases=biomarker.aliases,
        notes=biomarker.notes,
    )


def to_body_metric_out(metric: BodyMetric, user: User) -> BodyMetricOut:
    bands = bands_for(metric, user.sex)
    return BodyMetricOut(
        id=metric.id,
        slug=metric.slug,
        name=metric.name,
        unit=metric.unit,
        bands=[BandOut.model_validate(band) for band in bands] if bands is not None else None,
        source=metric.source,
        trend_reason=metric.trend_reason,
        notes=metric.notes,
    )


@router.get("/biomarkers", response_model=list[BiomarkerOut])
async def list_biomarkers(
    user: CurrentUser,
    db: DbSession,
    category: Annotated[BiomarkerCategory | None, Query()] = None,
) -> list[BiomarkerOut]:
    statement = (
        select(Biomarker)
        .where(or_(Biomarker.user_id.is_(None), Biomarker.user_id == user.id))
        .order_by(Biomarker.category, Biomarker.name)
    )
    if category is not None:
        statement = statement.where(Biomarker.category == category)
    biomarkers = (await db.execute(statement)).scalars().all()
    return [to_biomarker_out(biomarker, user) for biomarker in biomarkers]


@router.post("/biomarkers", response_model=BiomarkerOut, status_code=status.HTTP_201_CREATED)
async def create_custom_biomarker(
    payload: CustomBiomarkerCreate, user: CurrentUser, db: DbSession
) -> BiomarkerOut:
    biomarker = Biomarker(
        user_id=user.id,
        slug=f"custom-{user.id.hex[:8]}-{uuid.uuid4().hex[:12]}",
        name=payload.name.strip(),
        category=BiomarkerCategory.OUTRO,
        unit_default=payload.unit.strip(),
        canonical_unit=payload.unit.strip(),
        unit_conversions={},
        reference_kind=ReferenceKind.NONE,
        aliases=[payload.source_name.strip()] if payload.source_name else [],
        notes=(
            "Biomarcador personalizado. Consulta o profissional de saúde que pediu "
            "a análise para interpretar o resultado no teu contexto."
        ),
    )
    db.add(biomarker)
    await db.commit()
    await db.refresh(biomarker)
    return to_biomarker_out(biomarker, user)


@router.get("/body/metrics", response_model=list[BodyMetricOut])
async def list_body_metrics(user: CurrentUser, db: DbSession) -> list[BodyMetricOut]:
    statement = select(BodyMetric).order_by(BodyMetric.id)
    metrics = (await db.execute(statement)).scalars().all()
    return [to_body_metric_out(metric, user) for metric in metrics]


@router.get("/biomarkers/{biomarker_id}/series", response_model=BiomarkerSeries)
async def biomarker_series(biomarker_id: int, user: CurrentUser, db: DbSession) -> BiomarkerSeries:
    """Every result this user has for one biomarker, oldest first, plus the
    interventions running over that period."""
    biomarker = await db.get(Biomarker, biomarker_id)
    if biomarker is None or biomarker.user_id not in (None, user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Biomarker not found")

    statement = (
        select(Result, LabReport)
        .join(LabReport, Result.report_id == LabReport.id)
        .where(LabReport.user_id == user.id, Result.biomarker_id == biomarker_id)
        .order_by(LabReport.collected_on)
    )
    rows = (await db.execute(statement)).all()
    # The previous draw's assay and date travel forward, so a change of method
    # or a gap in the calendar shows as a discontinuity on the point where it
    # happened rather than nowhere at all.
    methods = [None, *(result.method for result, _ in rows)]
    collected_ons = [None, *(report.collected_on for _, report in rows)]
    points = [
        _to_point(result, report, previous_method, previous_collected_on)
        for (result, report), previous_method, previous_collected_on in zip(
            rows, methods, collected_ons, strict=False
        )
    ]
    interventions = await overlapping_interventions(
        db,
        user.id,
        points[0].date if points else None,
        points[-1].date if points else None,
    )

    start = points[0].date if points else None
    end = points[-1].date if points else None
    return BiomarkerSeries(
        biomarker=to_biomarker_out(biomarker, user),
        points=points,
        unit=biomarker.canonical_unit,
        has_unconverted_points=any(point.canonical_value is None for point in points),
        interventions=[InterventionOut.model_validate(item) for item in interventions],
        moments=await timeline.moments(db, user.id, start, end),
    )


def _to_point(
    result: Result,
    report: LabReport,
    previous_method: str | None,
    previous_collected_on: date | None,
) -> BiomarkerPoint:
    reference = Reference(
        result.reference_kind, result.ref_min, result.ref_max, result.reference_bands
    )
    return BiomarkerPoint(
        date=report.collected_on,
        value=result.value,
        unit=result.unit,
        canonical_value=result.canonical_value,
        lab_name=report.lab.name,
        ref_min=result.ref_min,
        ref_max=result.ref_max,
        canonical_ref_min=convert_bound(result.ref_min, result.conversion_factor),
        canonical_ref_max=convert_bound(result.ref_max, result.conversion_factor),
        reference_kind=result.reference_kind,
        band_label=(
            band_label(result.canonical_value, reference)
            if result.canonical_value is not None
            else None
        ),
        method=result.method,
        caveats=[
            CaveatOut(code=caveat.code, values=caveat.values)
            for caveat in caveats.for_point(result, report, previous_method, previous_collected_on)
        ],
        flag=result.flag,
        report_id=str(report.id),
    )
