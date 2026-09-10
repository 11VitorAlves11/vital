import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BiomarkerMatchRule(Base):
    """A reader-confirmed name mapping, scoped to one account and laboratory."""

    __tablename__ = "biomarker_match_rules"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "lab_name_normalised",
            "source_name_normalised",
            "source_unit_normalised",
            name="uq_biomarker_match_rules_source",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    biomarker_id: Mapped[int] = mapped_column(
        ForeignKey("biomarkers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lab_name: Mapped[str] = mapped_column(String(200), nullable=False)
    lab_name_normalised: Mapped[str] = mapped_column(String(200), nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_name_normalised: Mapped[str] = mapped_column(String(200), nullable=False)
    source_unit: Mapped[str | None] = mapped_column(String(50))
    # Empty string represents a missing unit so PostgreSQL uniqueness remains exact.
    source_unit_normalised: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

