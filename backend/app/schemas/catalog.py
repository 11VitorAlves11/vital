from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.models.enums import BiomarkerCategory


class BandOut(BaseModel):
    """A clinical band: `[min, max)`, null meaning unbounded on that side."""

    label: str
    min: float | None = None
    max: float | None = None
    flag: Literal["normal", "warn", "alert"]


class BiomarkerOut(BaseModel):
    id: int
    slug: str
    name: str
    category: BiomarkerCategory
    unit_default: str
    # Canonical range for the caller's sex; null when their sex is unknown.
    ref_min: Decimal | None = None
    ref_max: Decimal | None = None
    aliases: list[str]
    notes: str | None = None


class BodyMetricOut(BaseModel):
    id: int
    slug: str
    name: str
    unit: str
    # Null bands = trend-only metric: charted, never flagged.
    bands: list[BandOut] | None = None
    source: str | None = None
    notes: str | None = None
