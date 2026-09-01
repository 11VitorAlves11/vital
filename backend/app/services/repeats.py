"""Reminders to repeat one biomarker, and whether they still need to be.

A schedule is never marked fulfilled. Whether it still needs acting on is
derived at read time from whether a newer result exists — the same reasoning
flags are recomputed rather than cached (DT6) — against the collection date
the schedule snapshotted when it was created, so it survives the source report
being deleted later.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LabReport, Result, ScheduledRepeat

RepeatStatus = Literal["upcoming", "due", "fulfilled"]


def status_of(
    repeat: ScheduledRepeat, latest_collected_on: date | None, today: date
) -> RepeatStatus:
    if latest_collected_on is not None and latest_collected_on > repeat.source_collected_on:
        return "fulfilled"
    if (today.year, today.month) >= (repeat.target_year, repeat.target_month):
        return "due"
    return "upcoming"


async def latest_collected_on_by_biomarker(db: AsyncSession, user_id: uuid.UUID) -> dict[int, date]:
    """The most recent draw of every marker this account has ever had — the
    one fact every schedule's status is checked against."""
    statement = (
        select(Result.biomarker_id, func.max(LabReport.collected_on))
        .join(LabReport, Result.report_id == LabReport.id)
        .where(LabReport.user_id == user_id)
        .group_by(Result.biomarker_id)
    )
    rows = (await db.execute(statement)).all()
    return dict[int, date]((row[0], row[1]) for row in rows)


@dataclass(frozen=True, slots=True)
class RepeatWithStatus:
    repeat: ScheduledRepeat
    status: RepeatStatus


async def list_with_status(
    db: AsyncSession, user_id: uuid.UUID, today: date
) -> list[RepeatWithStatus]:
    statement = (
        select(ScheduledRepeat)
        .where(ScheduledRepeat.user_id == user_id)
        .order_by(ScheduledRepeat.target_year, ScheduledRepeat.target_month)
    )
    repeats = (await db.execute(statement)).scalars().all()
    latest = await latest_collected_on_by_biomarker(db, user_id)
    return [
        RepeatWithStatus(repeat, status_of(repeat, latest.get(repeat.biomarker_id), today))
        for repeat in repeats
    ]
