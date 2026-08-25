import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import Sex


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr | None
    name: str | None
    sex: Sex | None
    birth_date: date | None
    created_at: datetime


class UserUpdate(BaseModel):
    """Profile fields the user owns. `sex` drives every canonical range and band,
    so it is editable — and until it is set, no flag is inferred from it."""

    name: str | None = Field(default=None, max_length=200)
    sex: Sex | None = None
    birth_date: date | None = None
