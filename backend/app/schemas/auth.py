from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.core.security import MIN_PASSWORD_LENGTH
from app.models.enums import Sex


class AuthConfigOut(BaseModel):
    """Tells the frontend which login form to render."""

    mode: Literal["oidc", "local"]


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=72)
    name: str | None = Field(default=None, max_length=200)
    sex: Sex | None = None
    birth_date: date | None = None
    # Same bounds as UserUpdate.height_cm: a typo here moves every derived index
    # from the very first reading, without looking wrong on its own.
    height_cm: Decimal | None = Field(default=None, ge=100, le=250)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=72)
