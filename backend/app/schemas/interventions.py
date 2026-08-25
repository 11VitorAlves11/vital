import uuid
from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import InterventionKind


class InterventionCreate(BaseModel):
    kind: InterventionKind
    name: str = Field(min_length=1, max_length=200)
    dose: str | None = Field(default=None, max_length=100)
    started_on: date
    ended_on: date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _check_period(self) -> Self:
        if self.ended_on is not None and self.ended_on < self.started_on:
            raise ValueError("ended_on cannot precede started_on")
        return self


class InterventionUpdate(BaseModel):
    """PATCH: only the given fields change. `ended_on` is how an intervention ends."""

    kind: InterventionKind | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    dose: str | None = Field(default=None, max_length=100)
    started_on: date | None = None
    ended_on: date | None = None
    notes: str | None = None


class InterventionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: InterventionKind
    name: str
    dose: str | None
    started_on: date
    ended_on: date | None
    notes: str | None
