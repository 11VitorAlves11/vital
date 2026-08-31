"""Getting to the laboratory or doctor a typed name means.

Reports arrive carrying a name, not an id — from a form someone typed into or
from a PDF a model read. Turning that name into an entity has to be idempotent
under the spellings a human actually produces, or the same laboratory ends up in
the list three times and filtering the history by origin stops working.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Doctor, Lab
from app.services.text import normalise


async def _resolve[Provider: Lab | Doctor](
    db: AsyncSession, model: type[Provider], user_id: uuid.UUID, name: str
) -> Provider:
    """The account's entity for this name, created on first sight.

    Matched on the normalised name, stored under the name as typed: someone who
    writes "SYNLAB braga" today and "Synlab Braga" next year means one place, and
    the second spelling should not rename the first.
    """
    normalised = normalise(name)
    existing = (
        await db.execute(
            select(model).where(model.user_id == user_id, model.normalised_name == normalised)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    created = model(user_id=user_id, name=name.strip(), normalised_name=normalised)
    db.add(created)
    # Flushed rather than committed: the report being written in the same
    # transaction needs the id, and a rollback must take the entity with it.
    await db.flush()
    return created


async def lab_for(db: AsyncSession, user_id: uuid.UUID, name: str) -> Lab:
    return await _resolve(db, Lab, user_id, name)


async def doctor_for(db: AsyncSession, user_id: uuid.UUID, name: str | None) -> Doctor | None:
    if name is None or not name.strip():
        return None
    return await _resolve(db, Doctor, user_id, name)
