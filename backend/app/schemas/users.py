import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, model_validator

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


class ModelSettingsOut(BaseModel):
    model: str
    base_url: str | None
    has_api_key: bool
    has_account_api_key: bool
    uses_instance_model: bool
    uses_instance_base_url: bool


class ModelSettingsUpdate(BaseModel):
    model: str | None = Field(default=None, max_length=300)
    base_url: HttpUrl | None = None
    api_key: str | None = Field(default=None, min_length=1, max_length=4000)
    clear_api_key: bool = False

    @model_validator(mode="after")
    def api_key_action_is_unambiguous(self) -> "ModelSettingsUpdate":
        if self.api_key is not None and self.clear_api_key:
            raise ValueError("api_key and clear_api_key cannot be used together")
        return self
