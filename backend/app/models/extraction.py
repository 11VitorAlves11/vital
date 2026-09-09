import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import ExtractionStatus, pg_enum


class ExtractionJob(Base):
    """One PDF working its way through the extraction pipeline.

    `raw_output` keeps what the model actually answered, unedited. When a value
    in someone's history looks wrong months later, the question is whether the
    model misread it or a human confirmed it wrong, and only the untouched
    answer can tell the two apart.
    """

    __tablename__ = "extraction_jobs"
    __table_args__ = (UniqueConstraint("user_id", "file_sha256", name="uq_extraction_user_hash"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    file_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    media_type: Mapped[str] = mapped_column(String(50), nullable=False, default="application/pdf")
    filename: Mapped[str | None] = mapped_column(String)
    status: Mapped[ExtractionStatus] = mapped_column(
        pg_enum(ExtractionStatus, "extraction_status"),
        nullable=False,
        default=ExtractionStatus.PENDING,
        index=True,
    )
    # Provider and model as configured at the time, for audit: the instance can
    # be pointed at a different one between one report and the next.
    provider: Mapped[str | None] = mapped_column(String)
    raw_output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lab_reports.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
