"""Reminders to repeat one biomarker, created from a result.

The biomarker and the collection date that anchors fulfilment are both taken
from the result, never from the client — a schedule always says what it was
actually created against.
"""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import LabReport, Result, ScheduledRepeat
from app.schemas.repeats import RepeatStatus, ScheduledRepeatCreate, ScheduledRepeatOut
from app.services.repeats import list_with_status, status_of

router = APIRouter(prefix="/repeats", tags=["repeats"])


def to_repeat_out(repeat: ScheduledRepeat, status_: RepeatStatus) -> ScheduledRepeatOut:
    return ScheduledRepeatOut(
        id=repeat.id,
        biomarker_id=repeat.biomarker_id,
        biomarker_slug=repeat.biomarker.slug,
        biomarker_name=repeat.biomarker.name,
        target_year=repeat.target_year,
        target_month=repeat.target_month,
        note=repeat.note,
        created_at=repeat.created_at,
        source_result_id=repeat.source_result_id,
        status=status_,
    )


@router.get("", response_model=list[ScheduledRepeatOut])
async def list_repeats(
    user: CurrentUser,
    db: DbSession,
    status_filter: Annotated[RepeatStatus | None, Query(alias="status")] = None,
) -> list[ScheduledRepeatOut]:
    entries = await list_with_status(db, user.id, date.today())
    if status_filter is not None:
        entries = [entry for entry in entries if entry.status == status_filter]
    return [to_repeat_out(entry.repeat, entry.status) for entry in entries]


@router.post("", response_model=ScheduledRepeatOut, status_code=status.HTTP_201_CREATED)
async def create_repeat(
    payload: ScheduledRepeatCreate, user: CurrentUser, db: DbSession
) -> ScheduledRepeatOut:
    """Schedule a repeat from one result — the biomarker and the anchor date
    both come from it, so the two can never disagree with what was actually read."""
    statement = (
        select(Result, LabReport)
        .join(LabReport, Result.report_id == LabReport.id)
        .where(Result.id == payload.result_id, LabReport.user_id == user.id)
    )
    row = (await db.execute(statement)).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    result, report = row

    repeat = ScheduledRepeat(
        user_id=user.id,
        biomarker_id=result.biomarker_id,
        source_result_id=result.id,
        source_collected_on=report.collected_on,
        target_year=payload.target_year,
        target_month=payload.target_month,
        note=payload.note,
    )
    db.add(repeat)
    await db.commit()
    await db.refresh(repeat)
    # A schedule is fulfilled the moment it exists only if it was created
    # against a draw that is somehow already stale, which cannot happen here.
    return to_repeat_out(repeat, status_of(repeat, latest_collected_on=None, today=date.today()))


@router.delete("/{repeat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repeat(repeat_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    statement = select(ScheduledRepeat).where(
        ScheduledRepeat.id == repeat_id, ScheduledRepeat.user_id == user.id
    )
    repeat = (await db.execute(statement)).scalar_one_or_none()
    if repeat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    await db.delete(repeat)
    await db.commit()
