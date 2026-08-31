from decimal import Decimal
from typing import Any

from sqlalchemy import String, Text
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
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
