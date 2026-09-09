import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import Sex, pg_enum


class User(Base):
    """An account, created either from an OIDC subject or by local registration."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    oidc_sub: Mapped[str | None] = mapped_column(String, unique=True)
    email: Mapped[str | None] = mapped_column(String, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String)
    name: Mapped[str | None] = mapped_column(String)
    # Nullable because no OIDC provider is required to release it, and a guessed sex
    # silently applies the wrong reference ranges. Unknown means "no flag", never a default.
    sex: Mapped[Sex | None] = mapped_column(pg_enum(Sex, "sex"))
    birth_date: Mapped[date | None] = mapped_column(Date)
    # Height turns weight into BMI and fat-free mass into FFMI, which is where
    # almost every body-composition reference actually lives. Nullable for the
    # same reason as sex: without it those indices are not computed at all,
    # rather than computed against a guess.
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    # Optional per-account model override. The API key is encrypted with a key
    # kept in storage and is never included in a response.
    llm_model: Mapped[str | None] = mapped_column(String(300))
    llm_base_url: Mapped[str | None] = mapped_column(String(500))
    llm_api_key_encrypted: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
