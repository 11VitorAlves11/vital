"""Interventions — what the user was taking or doing, and when.

They exist to be overlaid on the trend charts, which is why the period matters more
than the detail: `ended_on = NULL` means still running.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import Intervention
from app.models.enums import InterventionKind
from app.schemas.interventions import InterventionCreate, InterventionOut, InterventionUpdate

router = APIRouter(prefix="/interventions", tags=["interventions"])


async def _owned(intervention_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Intervention:
    statement = select(Intervention).where(
        Intervention.id == intervention_id, Intervention.user_id == user.id
    )
    intervention = (await db.execute(statement)).scalar_one_or_none()
    if intervention is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intervention not found")
    return intervention


@router.get("", response_model=list[InterventionOut])
async def list_interventions(
    user: CurrentUser,
    db: DbSession,
    kind: Annotated[InterventionKind | None, Query()] = None,
) -> list[Intervention]:
    statement = (
        select(Intervention)
        .where(Intervention.user_id == user.id)
        .order_by(Intervention.started_on.desc())
    )
    if kind is not None:
        statement = statement.where(Intervention.kind == kind)
    return list((await db.execute(statement)).scalars().all())


@router.post("", response_model=InterventionOut, status_code=status.HTTP_201_CREATED)
async def create_intervention(
    payload: InterventionCreate, user: CurrentUser, db: DbSession
) -> Intervention:
    intervention = Intervention(user_id=user.id, **payload.model_dump())
    db.add(intervention)
    await db.commit()
    await db.refresh(intervention)
    return intervention


@router.patch("/{intervention_id}", response_model=InterventionOut)
async def update_intervention(
    intervention_id: uuid.UUID,
    payload: InterventionUpdate,
    user: CurrentUser,
    db: DbSession,
) -> Intervention:
    intervention = await _owned(intervention_id, user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(intervention, field, value)
    if intervention.ended_on is not None and intervention.ended_on < intervention.started_on:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="ended_on cannot precede started_on",
        )
    await db.commit()
    await db.refresh(intervention)
    return intervention


@router.delete("/{intervention_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_intervention(intervention_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    intervention = await _owned(intervention_id, user, db)
    await db.delete(intervention)
    await db.commit()
