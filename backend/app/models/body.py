import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import VALUE, Base
from app.models.enums import ScanSource, pg_enum


class BodyMetric(Base):
    """Shared catalogue entry, loaded from seed/body_metrics.json.

    `bands_m`/`bands_f` are `[{label, min, max, flag}]` covering the whole domain as
    `[min, max)` intervals. Both NULL means trend-only: recorded, charted, never flagged.
    A band whose `flag` is null names the reading without judging it — the scale is
    real, the verdict is not ours to give (see `trend_reason`).
    """

    __tablename__ = "body_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    unit: Mapped[str] = mapped_column(String, nullable=False)
    # none_as_null: a trend-only metric must be SQL NULL, not the JSON value `null`,
    # so "has no clinical bands" stays queryable.
    bands_m: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB(none_as_null=True))
    bands_f: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB(none_as_null=True))
    # `[{age_min, age_max, bands: [{label, min, max, flag}]}]` — the same band
    # shape as bands_m/bands_f, partitioned by age at the date of measurement,
    # `[age_min, age_max)`. Only body-fat-pct has these (5.3): a reference that
    # covers ages 20–79 has nothing to say about a 19- or 85-year-old, so a scan
    # outside every bracket simply carries no age context, not a guessed one.
    age_bands_m: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB(none_as_null=True))
    age_bands_f: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB(none_as_null=True))
    source: Mapped[str | None] = mapped_column(String)
    # Why this metric carries no verdict, in one line — set on every metric that
    # cannot produce a flag, whether it has no bands at all or bands that only
    # name (the ACE categories, which are fitness classes and not clinical ones).
    trend_reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)


class BodyScan(Base):
    """One weigh-in — every metric the scale reported in a single session."""

    __tablename__ = "body_scans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[ScanSource] = mapped_column(
        pg_enum(ScanSource, "scan_source"), nullable=False, default=ScanSource.MANUAL
    )
    device: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(Text)

    values: Mapped[list["BodyScanValue"]] = relationship(
        back_populates="scan", cascade="all, delete-orphan", lazy="selectin"
    )


class BodyScanValue(Base):
    """A metric reading. `flag` is always recomputed from the clinical bands —
    the scale's own rating is discarded on purpose."""

    __tablename__ = "body_scan_values"
    __table_args__ = (UniqueConstraint("scan_id", "metric_id", name="uq_scan_values_scan_metric"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("body_scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric_id: Mapped[int] = mapped_column(
        ForeignKey("body_metrics.id"), nullable=False, index=True
    )
    value: Mapped[Decimal] = mapped_column(VALUE, nullable=False)
    flag: Mapped[str | None] = mapped_column(Text)

    scan: Mapped[BodyScan] = relationship(back_populates="values")
    metric: Mapped[BodyMetric] = relationship(lazy="joined")
