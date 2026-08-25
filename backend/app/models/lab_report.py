import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import VALUE, Base
from app.models.biomarker import Biomarker
from app.models.enums import ReportSource, ResultFlag, pg_enum


class LabReport(Base):
    """One blood draw: the report the lab issued, with its individual results."""

    __tablename__ = "lab_reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    collected_on: Mapped[date] = mapped_column(Date, nullable=False)
    lab_name: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String)
    fasting: Mapped[bool | None] = mapped_column(Boolean)
    source: Mapped[ReportSource] = mapped_column(
        pg_enum(ReportSource, "report_source"), nullable=False, default=ReportSource.MANUAL
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    results: Mapped[list["Result"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", lazy="selectin"
    )


class Result(Base):
    """A single biomarker value, with the reference range the lab reported for it."""

    __tablename__ = "results"
    __table_args__ = (
        UniqueConstraint("report_id", "biomarker_id", name="uq_results_report_marker"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lab_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    biomarker_id: Mapped[int] = mapped_column(
        ForeignKey("biomarkers.id"), nullable=False, index=True
    )
    value: Mapped[Decimal] = mapped_column(VALUE, nullable=False)
    unit: Mapped[str] = mapped_column(String, nullable=False)
    ref_min: Mapped[Decimal | None] = mapped_column(VALUE)
    ref_max: Mapped[Decimal | None] = mapped_column(VALUE)
    # Computed server-side on write; NULL when neither the lab nor the catalogue
    # provides a range to compare against.
    flag: Mapped[ResultFlag | None] = mapped_column(pg_enum(ResultFlag, "result_flag"))

    report: Mapped[LabReport] = relationship(back_populates="results")
    biomarker: Mapped[Biomarker] = relationship(lazy="joined")
