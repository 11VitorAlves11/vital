import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, func
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
