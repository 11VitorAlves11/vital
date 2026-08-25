from decimal import Decimal

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import VALUE, Base
from app.models.enums import BiomarkerCategory, pg_enum


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
    # Canonical ranges are a fallback for manual entry; the lab's own range wins.
    ref_min_m: Mapped[Decimal | None] = mapped_column(VALUE)
    ref_max_m: Mapped[Decimal | None] = mapped_column(VALUE)
    ref_min_f: Mapped[Decimal | None] = mapped_column(VALUE)
    ref_max_f: Mapped[Decimal | None] = mapped_column(VALUE)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
