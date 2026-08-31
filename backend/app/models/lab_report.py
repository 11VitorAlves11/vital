import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import VALUE, Base
from app.models.biomarker import Biomarker
from app.models.enums import FastingState, ReferenceKind, ReportSource, ResultFlag, pg_enum


class LabReport(Base):
    """One blood draw: the report the lab issued, with its individual results."""

    __tablename__ = "lab_reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    collected_on: Mapped[date] = mapped_column(Date, nullable=False)
    # The wall-clock moment of the draw, without a zone: the diurnal peaks this
    # exists to catch are at a local hour, and a report never states an offset.
    # Its date always equals `collected_on`, which stays the column everything
    # sorts and filters by.
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    lab_name: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String)
    fasting_state: Mapped[FastingState] = mapped_column(
        pg_enum(FastingState, "fasting_state"), nullable=False, default=FastingState.UNKNOWN
    )
    #: Hours since the last meal, when the report or the reader states it.
    fasting_hours: Mapped[int | None] = mapped_column(SmallInteger)
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
    #: The value as the laboratory reported it, in `unit`. Never rewritten.
    value: Mapped[Decimal] = mapped_column(VALUE, nullable=False)
    unit: Mapped[str] = mapped_column(String, nullable=False)
    # The same reading in the catalogue's canonical unit, so a series stays one
    # continuous line when a lab switches from ng/mL to nmol/L. NULL when the
    # reported unit is not one we know how to convert.
    canonical_value: Mapped[Decimal | None] = mapped_column(VALUE)
    canonical_unit: Mapped[str | None] = mapped_column(String)
    #: value × conversion_factor = canonical_value. Stored so the conversion is
    #: auditable years later, when the catalogue's table may have been corrected.
    conversion_factor: Mapped[Decimal | None] = mapped_column(VALUE)
    ref_min: Mapped[Decimal | None] = mapped_column(VALUE)
    ref_max: Mapped[Decimal | None] = mapped_column(VALUE)
    # The assay behind the number ("hexoquinase", "picrato alcalino cinético").
    # Two labs measuring the same blood with different methods can differ by more
    # than the change being watched for, so the method travels with the result.
    method: Mapped[str | None] = mapped_column(String(120))
    #: Which of the four interval shapes `ref_min`/`ref_max`/`reference_bands` form.
    reference_kind: Mapped[ReferenceKind] = mapped_column(
        pg_enum(ReferenceKind, "reference_kind"), nullable=False, default=ReferenceKind.NONE
    )
    # Snapshot of the ordinal bands used for this draw, for the same reason the
    # range is stored per result: a later correction to the catalogue must not
    # silently reinterpret what was already read.
    reference_bands: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB(none_as_null=True))
    # Computed server-side on write; NULL when neither the lab nor the catalogue
    # provides a range to compare against.
    flag: Mapped[ResultFlag | None] = mapped_column(pg_enum(ResultFlag, "result_flag"))

    report: Mapped[LabReport] = relationship(back_populates="results")
    biomarker: Mapped[Biomarker] = relationship(lazy="joined")
