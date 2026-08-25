import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import InterventionKind, pg_enum


class Intervention(Base):
    """Something the user was doing over a period — overlaid on every trend chart."""

    __tablename__ = "interventions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[InterventionKind] = mapped_column(
        pg_enum(InterventionKind, "intervention_kind"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    dose: Mapped[str | None] = mapped_column(String)
    started_on: Mapped[date] = mapped_column(Date, nullable=False)
    ended_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
