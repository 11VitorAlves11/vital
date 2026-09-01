from datetime import time
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, SmallInteger, String, Text, Time, false
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import VALUE, Base
from app.models.enums import BiomarkerCategory, ReferenceKind, pg_enum


class Biomarker(Base):
    """Shared catalogue entry, loaded from seed/biomarkers.json."""

    __tablename__ = "biomarkers"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[BiomarkerCategory] = mapped_column(
        pg_enum(BiomarkerCategory, "biomarker_category"), nullable=False
    )
    unit_default: Mapped[str] = mapped_column(String, nullable=False)
    # The unit every value of this marker is normalised to before being charted.
    # Usually the same as `unit_default`; what makes it a separate column is that
    # `unit_default` is what a form pre-fills and this is what a series is in.
    canonical_unit: Mapped[str] = mapped_column(String, nullable=False)
    # {reported unit: factor to multiply by to reach `canonical_unit`}. A unit
    # absent from here is one we decline to convert rather than guess at.
    unit_conversions: Mapped[dict[str, float]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    # Canonical ranges are a fallback for manual entry; the lab's own range wins.
    reference_kind: Mapped[ReferenceKind] = mapped_column(
        pg_enum(ReferenceKind, "reference_kind"),
        nullable=False,
        default=ReferenceKind.TWO_SIDED,
    )
    ref_min_m: Mapped[Decimal | None] = mapped_column(VALUE)
    ref_max_m: Mapped[Decimal | None] = mapped_column(VALUE)
    ref_min_f: Mapped[Decimal | None] = mapped_column(VALUE)
    ref_max_f: Mapped[Decimal | None] = mapped_column(VALUE)
    # `[{label, min, max, flag}]` in `canonical_unit`, for the markers whose
    # reading is a named band rather than a pass/fail interval. NULL for the rest.
    ordinal_bands: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB(none_as_null=True))
    # Pre-analytical sensitivity: which markers a missing or wrong collection
    # context actually changes. Flagged per marker rather than per report,
    # because a non-fasted draw invalidates triglycerides and says nothing at
    # all about haemoglobin.
    fasting_sensitive: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    #: Hours of fasting the marker needs, when it needs any.
    fasting_min_hours: Mapped[int | None] = mapped_column(SmallInteger)
    time_sensitive: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    #: Local wall-clock window the draw should fall in, for the diurnal markers.
    time_window_start: Mapped[time | None] = mapped_column(Time)
    time_window_end: Mapped[time | None] = mapped_column(Time)
    # Markers whose level genuinely shifts through the calendar year (vitamin D,
    # sun-exposure dependent). Never used to guess a direction — the app has no
    # hemisphere to reason from — only to say that two draws far apart in the
    # calendar may differ partly because of when they were taken.
    seasonal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    # Assays whose result is worth reading with a caveat — never a reason to
    # hide the value, only to say why two labs may disagree about it.
    low_reliability_methods: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default="{}"
    )
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
