from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.models.enums import BiomarkerCategory, ReferenceKind, ResultFlag


class BandOut(BaseModel):
    """A body-composition band: `[min, max)`, null meaning unbounded on that side."""

    label: str
    min: float | None = None
    max: float | None = None
    # Null on a scale that names without judging: the ACE body-fat categories are
    # fitness classes, and calling one of them "normal" would lend them an
    # authority they do not have. The label still travels; the verdict does not.
    flag: Literal["normal", "warn", "alert"] | None = None


class ReferenceBandOut(BaseModel):
    """One step of an ordinal scale — "insuficiência", "normal" — in the canonical unit.

    Same shape as `BandOut`, different flag vocabulary: a lab result has no
    `warn`, so a band that is not `normal` is `low` or `high` like any other.
    """

    label: str
    min: float | None = None
    max: float | None = None
    flag: ResultFlag


class BiomarkerOut(BaseModel):
    id: int
    slug: str
    name: str
    category: BiomarkerCategory
    unit_default: str
    #: The unit every series of this marker is charted in.
    canonical_unit: str
    # The shape of the reference that applies *to this caller* — `none` when their
    # sex is unknown and the catalogue only has sex-specific ranges to offer.
    reference_kind: ReferenceKind
    # Canonical range for the caller's sex; null when their sex is unknown.
    ref_min: Decimal | None = None
    ref_max: Decimal | None = None
    # Set only for `ordinal_bands` markers, where the scale replaces the range.
    reference_bands: list[ReferenceBandOut] | None = None
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
    #: Why there is no verdict here, in one line. Set on every metric that cannot
    #: flag, so a card can say the reason instead of the same four words.
    trend_reason: str | None = None
    notes: str | None = None
