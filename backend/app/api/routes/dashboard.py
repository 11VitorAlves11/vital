"""The dashboard: one card per biomarker that has ever been measured, grouped by
the panel it is read in (haematology, iron, lipids, ...)."""

from collections import defaultdict
from datetime import date

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.api.routes.catalog import to_biomarker_out
from app.api.routes.repeats import to_repeat_out
from app.models import LabReport, Result
from app.models.enums import BiomarkerCategory
from app.schemas.dashboard import (
    SPARKLINE_POINTS,
    DashboardCategory,
    DashboardItem,
    DashboardOut,
    SparkPoint,
)
from app.services.flags import Reference, band_label
from app.services.repeats import list_with_status

router = APIRouter(tags=["dashboard"])


def _band_label(result: Result) -> str | None:
    if result.canonical_value is None:
        return None
    reference = Reference(
        result.reference_kind, result.ref_min, result.ref_max, result.reference_bands
    )
    return band_label(result.canonical_value, reference)


@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(user: CurrentUser, db: DbSession) -> DashboardOut:
    statement = (
        select(Result, LabReport)
        .join(LabReport, Result.report_id == LabReport.id)
        .where(LabReport.user_id == user.id)
        .order_by(LabReport.collected_on)
    )
    rows = (await db.execute(statement)).all()

    history: dict[int, list[tuple[Result, LabReport]]] = defaultdict(list)
    collected: set[date] = set()
    reports: set[str] = set()
    for result, report in rows:
        history[result.biomarker_id].append((result, report))
        collected.add(report.collected_on)
        reports.add(str(report.id))

    by_category: dict[BiomarkerCategory, list[DashboardItem]] = defaultdict(list)
    for entries in history.values():
        latest, latest_report = entries[-1]
        by_category[latest.biomarker.category].append(
            DashboardItem(
                biomarker=to_biomarker_out(latest.biomarker, user),
                value=latest.value,
                unit=latest.unit,
                flag=latest.flag,
                band_label=_band_label(latest),
                collected_on=latest_report.collected_on,
                lab_name=latest_report.lab.name,
                # Canonical, so a sparkline crossing a change of unit still shows
                # the shape of the history rather than a step that never happened.
                sparkline=[
                    SparkPoint(
                        date=report.collected_on,
                        value=result.canonical_value
                        if result.canonical_value is not None
                        else result.value,
                    )
                    for result, report in entries[-SPARKLINE_POINTS:]
                ],
            )
        )

    categories = [
        DashboardCategory(
            category=category,
            items=sorted(by_category[category], key=lambda item: item.biomarker.name),
        )
        for category in BiomarkerCategory
        if category in by_category
    ]
    due = [
        to_repeat_out(entry.repeat, entry.status)
        for entry in await list_with_status(db, user.id, date.today())
        if entry.status == "due"
    ]
    return DashboardOut(
        categories=categories,
        last_report_on=max(collected) if collected else None,
        report_count=len(reports),
        due_repeats=due,
    )
