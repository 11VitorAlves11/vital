"""The shared catalogues: biomarkers and body-composition metrics.

Both are global, but what a caller sees is not: reference ranges and clinical bands
are resolved for their sex before leaving the server, so no client ever has to pick.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import Biomarker, BodyMetric, LabReport, Result, User
from app.models.enums import BiomarkerCategory
from app.schemas.catalog import BandOut, BiomarkerOut, BodyMetricOut
from app.schemas.interventions import InterventionOut
from app.schemas.series import BiomarkerPoint, BiomarkerSeries
from app.services.bands import bands_for
from app.services.flags import canonical_range
from app.services.overlay import overlapping_interventions

router = APIRouter(tags=["catalogue"])


def to_biomarker_out(biomarker: Biomarker, user: User) -> BiomarkerOut:
    ref_min, ref_max = canonical_range(biomarker, user.sex)
    return BiomarkerOut(
        id=biomarker.id,
        slug=biomarker.slug,
        name=biomarker.name,
        category=biomarker.category,
        unit_default=biomarker.unit_default,
        ref_min=ref_min,
        ref_max=ref_max,
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
        notes=metric.notes,
    )


@router.get("/biomarkers", response_model=list[BiomarkerOut])
async def list_biomarkers(
    user: CurrentUser,
    db: DbSession,
    category: Annotated[BiomarkerCategory | None, Query()] = None,
) -> list[BiomarkerOut]:
    statement = select(Biomarker).order_by(Biomarker.category, Biomarker.name)
    if category is not None:
        statement = statement.where(Biomarker.category == category)
    biomarkers = (await db.execute(statement)).scalars().all()
    return [to_biomarker_out(biomarker, user) for biomarker in biomarkers]


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
    if biomarker is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Biomarker not found")

    statement = (
        select(Result, LabReport)
        .join(LabReport, Result.report_id == LabReport.id)
        .where(LabReport.user_id == user.id, Result.biomarker_id == biomarker_id)
        .order_by(LabReport.collected_on)
    )
    rows = (await db.execute(statement)).all()
    points = [
        BiomarkerPoint(
            date=report.collected_on,
            value=result.value,
            unit=result.unit,
            lab_name=report.lab_name,
            ref_min=result.ref_min,
            ref_max=result.ref_max,
            flag=result.flag,
            report_id=str(report.id),
        )
        for result, report in rows
    ]
    interventions = await overlapping_interventions(
        db,
        user.id,
        points[0].date if points else None,
        points[-1].date if points else None,
    )
    return BiomarkerSeries(
        biomarker=to_biomarker_out(biomarker, user),
        points=points,
        interventions=[InterventionOut.model_validate(item) for item in interventions],
    )
