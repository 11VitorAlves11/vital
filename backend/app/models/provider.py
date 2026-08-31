"""Where a report came from and who asked for it.

Both are per-account, not global. On a shared instance a global table of
laboratories would tell every account which ones the others use, and a
laboratory someone visits is not a fact about the software.

`normalised_name` is what uniqueness is measured on, so "Synlab Braga" typed
again with different case or spacing lands on the entity that already exists
rather than beside it. The name as typed is what gets shown back.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Lab(Base):
    __tablename__ = "labs"
    __table_args__ = (UniqueConstraint("user_id", "normalised_name", name="uq_labs_user_name"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    normalised_name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Doctor(Base):
    __tablename__ = "doctors"
    __table_args__ = (UniqueConstraint("user_id", "normalised_name", name="uq_doctors_user_name"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    normalised_name: Mapped[str] = mapped_column(String(200), nullable=False)
    specialty: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
