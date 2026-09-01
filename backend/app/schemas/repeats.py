import uuid
from datetime import date, datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

RepeatStatus = Literal["upcoming", "due", "fulfilled"]

#: How far out a repeat may be scheduled. Wide enough for "repeat this yearly",
#: narrow enough that a typo in the year does not silently vanish for decades.
MAX_YEARS_AHEAD = 5


class ScheduledRepeatCreate(BaseModel):
    #: The reading this reminder is against — resolves the biomarker server-side,
    #: so the client cannot send a biomarker that does not match its own result.
    result_id: uuid.UUID
    target_year: int
    target_month: int = Field(ge=1, le=12)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _check_target_is_a_real_future_month(self) -> Self:
        today = date.today()
        if (self.target_year, self.target_month) < (today.year, today.month):
            raise ValueError("target_year/target_month cannot be in the past")
        if self.target_year > today.year + MAX_YEARS_AHEAD:
            raise ValueError(f"target_year must be within {MAX_YEARS_AHEAD} years of today")
        return self


class ScheduledRepeatOut(BaseModel):
    id: uuid.UUID
    biomarker_id: int
    biomarker_slug: str
    biomarker_name: str
    target_year: int
    target_month: int
    note: str | None
    created_at: datetime
    #: Null once the source report is deleted — context only, never what
    #: fulfilment is checked against.
    source_result_id: uuid.UUID | None
    #: Derived on every read, never stored: whether a newer result already exists.
    status: RepeatStatus
