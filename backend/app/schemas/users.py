import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import Sex


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr | None
    name: str | None
    sex: Sex | None
    birth_date: date | None
    height_cm: Decimal | None
    created_at: datetime


class UserUpdate(BaseModel):
    """Profile fields the user owns. `sex` drives every canonical range and band,
    so it is editable — and until it is set, no flag is inferred from it."""

    name: str | None = Field(default=None, max_length=200)
    sex: Sex | None = None
    birth_date: date | None = None
    # Bounded at both ends: outside this range the number is a typo, and a typo
    # in height moves every derived index without looking wrong on its own.
    height_cm: Decimal | None = Field(default=None, ge=100, le=250)
