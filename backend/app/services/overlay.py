"""Which interventions to draw behind a series.

Only the ones whose period actually touches the plotted range: an overlay that
extends past the data invites reading a correlation that is not on the chart.
"""

import uuid
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Intervention


async def overlapping_interventions(
    db: AsyncSession, user_id: uuid.UUID, start: date | None, end: date | None
) -> list[Intervention]:
    if start is None or end is None:
        return []
    statement = (
        select(Intervention)
        .where(
            Intervention.user_id == user_id,
            Intervention.started_on <= end,
            or_(Intervention.ended_on.is_(None), Intervention.ended_on >= start),
        )
        .order_by(Intervention.started_on)
    )
    return list((await db.execute(statement)).scalars().all())
