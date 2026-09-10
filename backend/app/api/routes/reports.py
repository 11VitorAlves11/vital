"""Lab reports and their results.

Every query is filtered by the session user: there is no endpoint here that can
return another account's results, by id or otherwise.
"""

import re
import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import or_, select

from app.api.deps import CurrentUser, DbSession
from app.models import Biomarker, LabReport, Result
from app.models.enums import ReportSource, Sex
from app.schemas.catalog import ReferenceBandOut
from app.schemas.reports import (
    CaveatOut,
    ComparisonRow,
    ReportComparison,
    ReportCreate,
    ReportOut,
    ReportPatch,
    ReportSummary,
    ResultOut,
    ResultPatch,
    ResultPrefill,
)
from app.services import caveats, comparison, derived_biomarkers, providers, storage
from app.services import results as result_service
from app.services.flags import (
    Reference,
    band_label,
    canonical_reference,
    compute_flag,
    relative_position,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def utcnow() -> datetime:
    """When a note was written. Stored with a zone, unlike the collection hour:
    this is a moment in the log, not a local time on a clock."""
    return datetime.now(UTC)


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
        range_position=relative_position(result.value, reference),
        method=result.method,
        note=result.note,
        note_at=result.note_at,
        caveats=[
            CaveatOut(code=caveat.code, values=caveat.values)
            for caveat in caveats.for_result(result, report)
        ],
        flag=result.flag,
    )


def to_derived_result_out(
    item: derived_biomarkers.Derived,
    biomarker: Biomarker,
    sex: Sex | None,
    source_names: dict[str, str],
) -> ResultOut:
    """A computed value in the same shape as a measured one, minus everything
    that only exists because a lab actually printed a line: no id (nothing was
    stored), no note, no caveats about how it was drawn."""
    reference = canonical_reference(biomarker, sex)
    return ResultOut(
        id=None,
        biomarker_id=biomarker.id,
        biomarker_slug=biomarker.slug,
        biomarker_name=biomarker.name,
        category=biomarker.category,
        value=item.value,
        unit=biomarker.canonical_unit,
        canonical_value=item.value,
        canonical_unit=biomarker.canonical_unit,
        ref_min=reference.minimum,
        ref_max=reference.maximum,
        reference_kind=reference.kind,
        reference_bands=None,
        band_label=None,
        range_position=relative_position(item.value, reference),
        method=None,
        note=None,
        note_at=None,
        caveats=[],
        flag=compute_flag(item.value, reference),
        derived_from=[source_names[slug] for slug in item.source_slugs if slug in source_names],
    )


async def derived_results(report: LabReport, sex: Sex | None, db: DbSession) -> list[ResultOut]:
    """Every value this report's own numbers make computable but did not print,
    skipping anything it did — a lab's own LDL beats Friedewald's estimate."""
    measured = {
        result.biomarker.slug: result.canonical_value
        for result in report.results
        if result.canonical_value is not None
    }
    items = derived_biomarkers.derive(measured)
    if not items:
        return []

    slugs = {item.biomarker_slug for item in items} | {
        source for item in items for source in item.source_slugs
    }
    statement = select(Biomarker).where(Biomarker.slug.in_(slugs))
    catalogue = {row.slug: row for row in (await db.execute(statement)).scalars().all()}
    source_names = {slug: row.name for slug, row in catalogue.items()}
    return [
        to_derived_result_out(item, catalogue[item.biomarker_slug], sex, source_names)
        for item in items
        if item.biomarker_slug in catalogue
    ]


def to_report_summary(report: LabReport) -> ReportSummary:
    return ReportSummary(
        id=report.id,
        collected_on=report.collected_on,
        collected_at=report.collected_at,
        lab_id=report.lab_id,
        lab_name=report.lab.name,
        doctor_id=report.doctor_id,
        doctor_name=report.doctor.name if report.doctor else None,
        fasting_state=report.fasting_state,
        fasting_hours=report.fasting_hours,
        source=report.source,
        notes=report.notes,
        notes_at=report.notes_at,
        created_at=report.created_at,
        result_count=len(report.results),
        has_file=bool(report.file_path),
    )


async def to_report_out(report: LabReport, sex: Sex | None, db: DbSession) -> ReportOut:
    results = [to_result_out(result, report) for result in report.results]
    results += await derived_results(report, sex, db)
    return ReportOut(
        id=report.id,
        collected_on=report.collected_on,
        collected_at=report.collected_at,
        lab_id=report.lab_id,
        lab_name=report.lab.name,
        doctor_id=report.doctor_id,
        doctor_name=report.doctor.name if report.doctor else None,
        fasting_state=report.fasting_state,
        fasting_hours=report.fasting_hours,
        source=report.source,
        notes=report.notes,
        notes_at=report.notes_at,
        created_at=report.created_at,
        has_file=bool(report.file_path),
        results=results,
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
    lab_id: Annotated[uuid.UUID | None, Query()] = None,
    doctor_id: Annotated[uuid.UUID | None, Query()] = None,
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
    # Filtering by origin: the lab id came from this account's own list, and the
    # user_id above still bounds the query, so an id from elsewhere finds nothing.
    if lab_id is not None:
        statement = statement.where(LabReport.lab_id == lab_id)
    if doctor_id is not None:
        statement = statement.where(LabReport.doctor_id == doctor_id)
    reports = (await db.execute(statement)).scalars().all()
    return [to_report_summary(report) for report in reports]


@router.get("/prefill", response_model=list[ResultPrefill])
async def prefill(
    user: CurrentUser,
    db: DbSession,
    lab_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[ResultPrefill]:
    """The most recent reading of every marker this account has ever recorded.

    Manual entry is otherwise five fields per line, four of which have not
    changed since the last visit to the same laboratory. Narrowed to that
    laboratory when one is given; without it the latest reading anywhere is
    offered instead, marked `same_lab: false` — the unit and the assay travel
    between laboratories, and the reference range does not.
    """
    statement = (
        select(Result, LabReport)
        .join(LabReport, Result.report_id == LabReport.id)
        .where(LabReport.user_id == user.id)
        .distinct(Result.biomarker_id)
        .order_by(
            Result.biomarker_id,
            LabReport.collected_on.desc(),
            LabReport.created_at.desc(),
        )
    )
    if lab_id is not None:
        statement = statement.where(LabReport.lab_id == lab_id)

    return [
        ResultPrefill(
            biomarker_id=result.biomarker_id,
            unit=result.unit,
            ref_min=result.ref_min,
            ref_max=result.ref_max,
            method=result.method,
            lab_name=report.lab.name,
            collected_on=report.collected_on,
            same_lab=lab_id is not None,
        )
        for result, report in (await db.execute(statement)).all()
    ]


@router.get("/compare", response_model=ReportComparison)
async def compare_reports(
    user: CurrentUser,
    db: DbSession,
    a: Annotated[uuid.UUID, Query()],
    b: Annotated[uuid.UUID, Query()],
) -> ReportComparison:
    """Two collections marker by marker, with what moved between them.

    Which one is `a` and which is `b` does not matter: the pair is ordered by the
    date of the draw before anything is subtracted, so a difference always reads
    forward in time.
    """
    if a == b:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A report cannot be compared with itself",
        )
    # Both go through the ownership check; neither id can reach another account's
    # report, and a comparison is not a way around that.
    pair = [await _owned_report(a, user, db), await _owned_report(b, user, db)]
    previous, current = sorted(pair, key=lambda report: (report.collected_on, report.created_at))

    return ReportComparison(
        previous=to_report_summary(previous),
        current=to_report_summary(current),
        rows=[
            ComparisonRow(
                biomarker_id=row.biomarker.id,
                biomarker_slug=row.biomarker.slug,
                biomarker_name=row.biomarker.name,
                category=row.biomarker.category,
                previous=to_result_out(row.previous, previous) if row.previous else None,
                current=to_result_out(row.current, current) if row.current else None,
                delta=row.delta,
                percent_change=row.percent_change,
                unit=row.unit,
                caveats=[
                    CaveatOut(code=caveat.code, values=caveat.values) for caveat in row.caveats
                ],
            )
            for row in comparison.compare(previous, current)
        ],
    )


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def create_report(payload: ReportCreate, user: CurrentUser, db: DbSession) -> ReportOut:
    """Create a report and its results in one go, flagging each value server-side."""
    requested = [result.biomarker_id for result in payload.results]
    catalogue = {
        biomarker.id: biomarker
        for biomarker in (
            (
                await db.execute(
                    select(Biomarker).where(
                        Biomarker.id.in_(requested),
                        or_(Biomarker.user_id.is_(None), Biomarker.user_id == user.id),
                    )
                )
            )
            .scalars()
            .all()
        )
    }
    unknown = sorted(set(requested) - catalogue.keys())
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown biomarker ids: {unknown}",
        )

    lab = await providers.lab_for(db, user.id, payload.lab_name)
    doctor = await providers.doctor_for(db, user.id, payload.doctor_name)
    report = LabReport(
        user_id=user.id,
        collected_on=payload.collected_on,
        collected_at=payload.collected_at,
        lab_id=lab.id,
        doctor_id=doctor.id if doctor else None,
        fasting_state=payload.fasting_state,
        fasting_hours=payload.fasting_hours,
        notes=payload.notes,
        notes_at=utcnow() if payload.notes else None,
        source=ReportSource.MANUAL,
    )
    for entry in payload.results:
        biomarker = catalogue[entry.biomarker_id]
        result = result_service.build(
            biomarker,
            user.sex,
            entry.value,
            entry.unit,
            entry.ref_min,
            entry.ref_max,
            entry.method,
        )
        if entry.note:
            result.note, result.note_at = entry.note, utcnow()
        report.results.append(result)

    db.add(report)
    await db.commit()
    await db.refresh(report)
    return await to_report_out(report, user.sex, db)


@router.get("/{report_id}", response_model=ReportOut)
async def read_report(report_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ReportOut:
    report = await _owned_report(report_id, user, db)
    return await to_report_out(report, user.sex, db)


@router.patch("/{report_id}", response_model=ReportOut)
async def update_report(
    report_id: uuid.UUID, payload: ReportPatch, user: CurrentUser, db: DbSession
) -> ReportOut:
    """The interpretive note on the collection, and who ordered it.

    Only the fields a reader adds after the fact. The values themselves are not
    editable: a wrong number is a wrong reading, and correcting it in place would
    leave no trace that it was ever anything else.
    """
    report = await _owned_report(report_id, user, db)
    fields = payload.model_dump(exclude_unset=True)

    # Stamped only when the text actually moves, so re-saving an unchanged note
    # does not make a year-old reading look like today's.
    if "notes" in fields and fields["notes"] != report.notes:
        report.notes, report.notes_at = fields["notes"], utcnow()
    if "doctor_name" in fields:
        doctor = await providers.doctor_for(db, user.id, fields["doctor_name"])
        report.doctor_id = doctor.id if doctor else None

    await db.commit()
    await db.refresh(report)
    return await to_report_out(report, user.sex, db)


@router.patch("/{report_id}/results/{result_id}", response_model=ResultOut)
async def update_result(
    report_id: uuid.UUID,
    result_id: uuid.UUID,
    payload: ResultPatch,
    user: CurrentUser,
    db: DbSession,
) -> ResultOut:
    """A note against one value — "colheita às 11:30, fora da janela"."""
    report = await _owned_report(report_id, user, db)
    result = next((item for item in report.results if item.id == result_id), None)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    fields = payload.model_dump(exclude_unset=True)
    if "note" in fields and fields["note"] != result.note:
        result.note, result.note_at = fields["note"], utcnow()

    await db.commit()
    await db.refresh(result)
    return to_result_out(result, report)


@router.get("/{report_id}/file")
async def read_report_file(report_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Response:
    """The original PDF or photographed report, for an extracted report.

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
    label = re.sub(r"[^A-Za-z0-9 ._-]", "", report.lab.name).strip() or "report"
    media_type = storage.media_type_for(content) or "application/octet-stream"
    suffix = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png"}.get(
        media_type, "bin"
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={
            # inline, so the browser shows it instead of downloading it, and a
            # filename built from the report rather than from the upload.
            "Content-Disposition": f'inline; filename="{report.collected_on}-{label}.{suffix}"',
            "Cache-Control": "private, no-store",
        },
    )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(report_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    report = await _owned_report(report_id, user, db)
    await db.delete(report)
    await db.commit()
