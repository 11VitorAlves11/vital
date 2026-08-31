"""Lab reports and their results.

Every query is filtered by the session user: there is no endpoint here that can
return another account's results, by id or otherwise.
"""

import re
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import Biomarker, LabReport, Result
from app.models.enums import ReportSource
from app.schemas.catalog import ReferenceBandOut
from app.schemas.reports import CaveatOut, ReportCreate, ReportOut, ReportSummary, ResultOut
from app.services import caveats, storage
from app.services import results as result_service
from app.services.flags import Reference, band_label

router = APIRouter(prefix="/reports", tags=["reports"])


def to_result_out(result: Result, report: LabReport) -> ResultOut:
    reference = Reference(
        result.reference_kind, result.ref_min, result.ref_max, result.reference_bands
    )
    return ResultOut(
        id=result.id,
        biomarker_id=result.biomarker_id,
        biomarker_slug=result.biomarker.slug,
        biomarker_name=result.biomarker.name,
        category=result.biomarker.category,
        value=result.value,
        unit=result.unit,
        canonical_value=result.canonical_value,
        canonical_unit=result.canonical_unit,
        ref_min=result.ref_min,
        ref_max=result.ref_max,
        reference_kind=result.reference_kind,
        reference_bands=(
            [ReferenceBandOut.model_validate(band) for band in result.reference_bands]
            if result.reference_bands
            else None
        ),
        # Named only for the ordinal scales, and read off the canonical value:
        # the bands are catalogued in the canonical unit, not the reported one.
        band_label=(
            band_label(result.canonical_value, reference)
            if result.canonical_value is not None
            else None
        ),
        method=result.method,
        caveats=[
            CaveatOut(code=caveat.code, values=caveat.values)
            for caveat in caveats.for_result(result, report)
        ],
        flag=result.flag,
    )


def to_report_out(report: LabReport) -> ReportOut:
    return ReportOut(
        id=report.id,
        collected_on=report.collected_on,
        collected_at=report.collected_at,
        lab_name=report.lab_name,
        fasting_state=report.fasting_state,
        fasting_hours=report.fasting_hours,
        source=report.source,
        notes=report.notes,
        created_at=report.created_at,
        has_file=bool(report.file_path),
        results=[to_result_out(result, report) for result in report.results],
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
            collected_at=report.collected_at,
            lab_name=report.lab_name,
            fasting_state=report.fasting_state,
            fasting_hours=report.fasting_hours,
            source=report.source,
            notes=report.notes,
            created_at=report.created_at,
            result_count=len(report.results),
            has_file=bool(report.file_path),
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
        collected_at=payload.collected_at,
        lab_name=payload.lab_name,
        fasting_state=payload.fasting_state,
        fasting_hours=payload.fasting_hours,
        notes=payload.notes,
        source=ReportSource.MANUAL,
    )
    for entry in payload.results:
        biomarker = catalogue[entry.biomarker_id]
        report.results.append(
            result_service.build(
                biomarker,
                user.sex,
                entry.value,
                entry.unit,
                entry.ref_min,
                entry.ref_max,
                entry.method,
            )
        )

    db.add(report)
    await db.commit()
    await db.refresh(report)
    return to_report_out(report)


@router.get("/{report_id}", response_model=ReportOut)
async def read_report(report_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ReportOut:
    return to_report_out(await _owned_report(report_id, user, db))


@router.get("/{report_id}/file")
async def read_report_file(report_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Response:
    """The original PDF, for a report that came from one.

    Served through the API rather than from a static path: the file holds
    someone's blood work, and the only thing standing between it and the open
    internet is this ownership check.
    """
    report = await _owned_report(report_id, user, db)
    content = storage.read_file(report.file_path) if report.file_path else None
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No file for this report")
    # The lab name is whatever the account typed, and it lands in a header:
    # anything but plain characters is dropped rather than escaped.
    label = re.sub(r"[^A-Za-z0-9 ._-]", "", report.lab_name).strip() or "report"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            # inline, so the browser shows it instead of downloading it, and a
            # filename built from the report rather than from the upload.
            "Content-Disposition": f'inline; filename="{report.collected_on}-{label}.pdf"',
            "Cache-Control": "private, no-store",
        },
    )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(report_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    report = await _owned_report(report_id, user, db)
    await db.delete(report)
    await db.commit()
