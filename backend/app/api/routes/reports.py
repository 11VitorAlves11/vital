"""Lab reports and their results.

Every query is filtered by the session user: there is no endpoint here that can
return another account's results, by id or otherwise.
"""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import Biomarker, LabReport, Result
from app.models.enums import ReportSource
from app.schemas.reports import ReportCreate, ReportOut, ReportSummary, ResultOut
from app.services.flags import compute_flag, effective_range

router = APIRouter(prefix="/reports", tags=["reports"])


def to_result_out(result: Result) -> ResultOut:
    return ResultOut(
        id=result.id,
        biomarker_id=result.biomarker_id,
        biomarker_slug=result.biomarker.slug,
        biomarker_name=result.biomarker.name,
        category=result.biomarker.category,
        value=result.value,
        unit=result.unit,
        ref_min=result.ref_min,
        ref_max=result.ref_max,
        flag=result.flag,
    )


def to_report_out(report: LabReport) -> ReportOut:
    return ReportOut(
        id=report.id,
        collected_on=report.collected_on,
        lab_name=report.lab_name,
        fasting=report.fasting,
        source=report.source,
        notes=report.notes,
        created_at=report.created_at,
        results=[to_result_out(result) for result in report.results],
    )


async def _owned_report(report_id: uuid.UUID, user: CurrentUser, db: DbSession) -> LabReport:
    statement = select(LabReport).where(LabReport.id == report_id, LabReport.user_id == user.id)
    report = (await db.execute(statement)).scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@router.get("", response_model=list[ReportSummary])
async def list_reports(
    user: CurrentUser,
    db: DbSession,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
) -> list[ReportSummary]:
    statement = (
        select(LabReport)
        .where(LabReport.user_id == user.id)
        .order_by(LabReport.collected_on.desc(), LabReport.created_at.desc())
    )
    if date_from is not None:
        statement = statement.where(LabReport.collected_on >= date_from)
    if date_to is not None:
        statement = statement.where(LabReport.collected_on <= date_to)
    reports = (await db.execute(statement)).scalars().all()
    return [
        ReportSummary(
            id=report.id,
            collected_on=report.collected_on,
            lab_name=report.lab_name,
            fasting=report.fasting,
            source=report.source,
            notes=report.notes,
            created_at=report.created_at,
            result_count=len(report.results),
        )
        for report in reports
    ]


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def create_report(payload: ReportCreate, user: CurrentUser, db: DbSession) -> ReportOut:
    """Create a report and its results in one go, flagging each value server-side."""
    requested = [result.biomarker_id for result in payload.results]
    catalogue = {
        biomarker.id: biomarker
        for biomarker in (
            (await db.execute(select(Biomarker).where(Biomarker.id.in_(requested)))).scalars().all()
        )
    }
    unknown = sorted(set(requested) - catalogue.keys())
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown biomarker ids: {unknown}",
        )

    report = LabReport(
        user_id=user.id,
        collected_on=payload.collected_on,
        lab_name=payload.lab_name,
        fasting=payload.fasting,
        notes=payload.notes,
        source=ReportSource.MANUAL,
    )
    for entry in payload.results:
        biomarker = catalogue[entry.biomarker_id]
        reference = effective_range(biomarker, user.sex, entry.ref_min, entry.ref_max)
        report.results.append(
            Result(
                biomarker_id=biomarker.id,
                value=entry.value,
                unit=entry.unit or biomarker.unit_default,
                ref_min=entry.ref_min,
                ref_max=entry.ref_max,
                flag=compute_flag(entry.value, reference),
            )
        )

    db.add(report)
    await db.commit()
    await db.refresh(report)
    return to_report_out(report)


@router.get("/{report_id}", response_model=ReportOut)
async def read_report(report_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ReportOut:
    return to_report_out(await _owned_report(report_id, user, db))


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(report_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    report = await _owned_report(report_id, user, db)
    await db.delete(report)
    await db.commit()
