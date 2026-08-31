"""One chronological view of everything an account has recorded.

Paged by date rather than by offset: the history grows at the recent end, and an
offset would shift every page under the reader the moment a report is added.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.models.enums import TimelineKind
from app.schemas.timeline import PAGE_SIZE, TimelineOut
from app.services import timeline

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("", response_model=TimelineOut)
async def read_timeline(
    user: CurrentUser,
    db: DbSession,
    kinds: Annotated[list[TimelineKind] | None, Query()] = None,
    before: Annotated[date | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = PAGE_SIZE,
) -> TimelineOut:
    page = await timeline.collect(db, user.id, kinds, before, limit)
    return TimelineOut(
        events=page.events,
        # From the whole history, not this page: the filter must not lose an
        # option as the reader scrolls past the last event of that kind.
        available_kinds=await timeline.available_kinds(db, user.id),
        next_before=page.next_before,
    )
