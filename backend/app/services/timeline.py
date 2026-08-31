"""Everything that happened, in one chronological list.

Four tables with nothing in common but a date, turned into one shape the client
can render without knowing which table a row came from. The wording is done here
rather than in the client because there is one server and several clients, and
"3 fora do intervalo" should read the same in all of them.

Events are built per page: the query pulls a window of each source, merges, and
cuts. It is not the cheapest possible approach, and at the scale of one person's
medical history — hundreds of rows, not millions — it is the one worth having.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.models import BodyScan, Intervention, LabReport, ProgressPhoto
from app.models.enums import ResultFlag, TimelineKind
from app.schemas.timeline import TimelineEvent, TimelineSummaryItem

#: Sorts an all-day event against a timed one on the same day: the timed one
#: happened at a known hour, the all-day one is placed before it rather than
#: pretending to a midnight it never had.
_ALL_DAY = datetime.min


def _report_event(report: LabReport) -> TimelineEvent:
    out_of_range = [
        result
        for result in report.results
        if result.flag is not None and result.flag is not ResultFlag.NORMAL
    ]
    return TimelineEvent(
        id=f"lab_report:{report.id}",
        kind=TimelineKind.LAB_REPORT,
        occurred_on=report.collected_on,
        # The hour of a draw changes how its values read; it belongs on the card.
        occurred_at=report.collected_at,
        title=report.lab.name,
        subtitle=report.doctor.name if report.doctor else None,
        summary=[
            TimelineSummaryItem(
                label=result.biomarker.name,
                value=f"{_trim(result.value)} {result.unit}",
                flag=result.flag,
            )
            # Out of range first and capped: a card is a summary, and a report
            # with forty normal values has nothing to say beyond its count.
            for result in sorted(out_of_range, key=lambda item: item.biomarker.name)[:4]
        ],
        href=f"/reports/{report.id}",
    )


def _scan_event(scan: BodyScan) -> TimelineEvent:
    return TimelineEvent(
        id=f"body_composition:{scan.id}",
        kind=TimelineKind.BODY_COMPOSITION,
        occurred_on=scan.measured_at.date(),
        occurred_at=scan.measured_at.replace(tzinfo=None),
        title=scan.device or "",
        summary=[
            TimelineSummaryItem(
                label=value.metric.name,
                value=f"{_trim(value.value)} {value.metric.unit}",
            )
            for value in sorted(scan.values, key=lambda item: item.metric_id)[:4]
        ],
        href="/body",
    )


def _photo_event(photo: ProgressPhoto) -> TimelineEvent:
    return TimelineEvent(
        id=f"progress_photo:{photo.id}",
        kind=TimelineKind.PROGRESS_PHOTO,
        occurred_on=photo.taken_on,
        title="",
        pose=photo.pose,
        photo_id=photo.id,
        href="/photos",
    )


def _intervention_event(intervention: Intervention) -> TimelineEvent:
    return TimelineEvent(
        id=f"intervention:{intervention.id}",
        kind=TimelineKind.INTERVENTION,
        occurred_on=intervention.started_on,
        ended_on=intervention.ended_on,
        # A period, even an open-ended one: the rail draws a bar from the start
        # to the end or to today, never a single node at the start.
        has_duration=True,
        title=intervention.name,
        subtitle=intervention.dose,
        intervention_kind=intervention.kind,
        href="/interventions",
    )


def _trim(value: object) -> str:
    """Numeric(12,4) prints as "14.1000"; nobody writes a haemoglobin that way."""
    text = f"{value}"
    return text.rstrip("0").rstrip(".") if "." in text else text


async def _page[Row](
    db: AsyncSession,
    statement: Select[tuple[Row]],
    cursor: InstrumentedAttribute[Any],
    before: date | None,
    limit: int,
) -> Sequence[Row]:
    """The newest rows strictly older than the cursor.

    One more than the page asks for, from every source. A source that returns
    exactly a page's worth may have more behind it, and the extra row is what
    tells "this is the end of the history" apart from "this is the end of the
    page" — and whether the last day of the page is whole.
    """
    if before is not None:
        statement = statement.where(cursor < before)
    result = await db.execute(statement.order_by(cursor.desc()).limit(limit + 1))
    return result.scalars().all()


@dataclass(frozen=True, slots=True)
class Page:
    events: list[TimelineEvent]
    #: The cursor to ask for the next page with, or None at the end of history.
    next_before: date | None


async def collect(
    db: AsyncSession,
    user_id: uuid.UUID,
    kinds: Sequence[TimelineKind] | None,
    before: date | None,
    limit: int,
) -> Page:
    """A page of events, newest first, across every source at once."""
    wanted = set(kinds) if kinds else None
    events: list[TimelineEvent] = []

    if wanted is None or TimelineKind.LAB_REPORT in wanted:
        events += [
            _report_event(report)
            for report in await _page(
                db,
                select(LabReport).where(LabReport.user_id == user_id),
                LabReport.collected_on,
                before,
                limit,
            )
        ]

    if wanted is None or TimelineKind.BODY_COMPOSITION in wanted:
        events += [
            _scan_event(scan)
            for scan in await _page(
                db,
                select(BodyScan).where(BodyScan.user_id == user_id),
                BodyScan.measured_at,
                before,
                limit,
            )
        ]

    if wanted is None or TimelineKind.PROGRESS_PHOTO in wanted:
        events += [
            _photo_event(photo)
            for photo in await _page(
                db,
                select(ProgressPhoto).where(ProgressPhoto.user_id == user_id),
                ProgressPhoto.taken_on,
                before,
                limit,
            )
        ]

    if wanted is None or TimelineKind.INTERVENTION in wanted:
        events += [
            _intervention_event(item)
            for item in await _page(
                db,
                select(Intervention).where(Intervention.user_id == user_id),
                Intervention.started_on,
                before,
                limit,
            )
        ]

    events.sort(key=lambda event: (event.occurred_on, event.occurred_at or _ALL_DAY), reverse=True)

    # Every source was asked for one row more than the page holds, so a merged
    # list that still fits means every source is exhausted: end of the history.
    if len(events) <= limit:
        return Page(events, None)

    # Otherwise the cursor is the last day of the page, and the next request
    # asks for everything strictly older — so the page has to end on a day it
    # has all of, or the rest of that day would appear in neither page. The one
    # exception is a day that fills a page on its own, where there is no
    # boundary to cut at and the alternative is a page with nothing in it.
    page = events[:limit]
    if events[limit].occurred_on == page[-1].occurred_on:
        page = [event for event in page if event.occurred_on != page[-1].occurred_on] or page
    return Page(page, page[-1].occurred_on)


async def moments(
    db: AsyncSession, user_id: uuid.UUID, start: date | None, end: date | None
) -> list[TimelineEvent]:
    """Point events inside a plotted period, for annotating a chart.

    Lab reports are left out: on a biomarker chart they are the points, and a
    vertical rule through every one of them annotates nothing. Interventions are
    left out too — they have duration and are drawn as bands, not lines.
    """
    if start is None or end is None:
        return []

    scans = (
        await db.execute(
            select(BodyScan).where(
                BodyScan.user_id == user_id,
                BodyScan.measured_at >= datetime.combine(start, time.min, tzinfo=UTC),
                BodyScan.measured_at <= datetime.combine(end, time.max, tzinfo=UTC),
            )
        )
    ).scalars()
    photos = (
        await db.execute(
            select(ProgressPhoto).where(
                ProgressPhoto.user_id == user_id,
                ProgressPhoto.taken_on >= start,
                ProgressPhoto.taken_on <= end,
            )
        )
    ).scalars()

    events = [_scan_event(scan) for scan in scans] + [_photo_event(photo) for photo in photos]
    events.sort(key=lambda event: event.occurred_on)
    return events


async def available_kinds(db: AsyncSession, user_id: uuid.UUID) -> list[TimelineKind]:
    """The kinds this account has anything of, in the order the filter shows them."""
    present: list[TimelineKind] = []
    for kind, statement in (
        (TimelineKind.LAB_REPORT, select(LabReport.id).where(LabReport.user_id == user_id)),
        (TimelineKind.BODY_COMPOSITION, select(BodyScan.id).where(BodyScan.user_id == user_id)),
        (
            TimelineKind.PROGRESS_PHOTO,
            select(ProgressPhoto.id).where(ProgressPhoto.user_id == user_id),
        ),
        (TimelineKind.INTERVENTION, select(Intervention.id).where(Intervention.user_id == user_id)),
    ):
        if (await db.execute(statement.limit(1))).first() is not None:
            present.append(kind)
    return present
