"""Classification of lab results against a reference interval.

Three states only — `low`, `normal`, `high`. There is deliberately no borderline
state: the interval comes from the laboratory itself and there is no clinical basis
for inventing a margin around it.

An interval is not always two numbers. `ReferenceKind` names the four shapes a
report actually uses, and each is flagged on its own terms: an upper bound says
nothing about how low is too low, so a value under it is `normal`, not `low`.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.models.biomarker import Biomarker
from app.models.enums import ReferenceKind, ResultFlag, Sex


@dataclass(frozen=True, slots=True)
class Reference:
    """The interval a single value is read against, whatever shape it takes."""

    kind: ReferenceKind
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    #: `[{label, min, max, flag}]`, only for `ordinal_bands`.
    bands: list[dict[str, Any]] | None = None


NO_REFERENCE = Reference(ReferenceKind.NONE)


def bounded(minimum: Decimal | None, maximum: Decimal | None) -> Reference:
    """Name the shape two nullable bounds happen to form."""
    if minimum is not None and maximum is not None:
        return Reference(ReferenceKind.TWO_SIDED, minimum, maximum)
    if maximum is not None:
        return Reference(ReferenceKind.UPPER_BOUND, maximum=maximum)
    if minimum is not None:
        return Reference(ReferenceKind.LOWER_BOUND, minimum=minimum)
    return NO_REFERENCE


def canonical_reference(biomarker: Biomarker, sex: Sex | None) -> Reference:
    """The catalogue's own interval for this user — a fallback, never the primary source.

    Ordinal bands are the exception: they are a clinical consensus scale rather
    than one analyser's range, they are the same for both sexes, and they are the
    reason the marker was catalogued as ordinal in the first place.
    """
    if biomarker.reference_kind is ReferenceKind.ORDINAL_BANDS:
        if not biomarker.ordinal_bands:
            return NO_REFERENCE
        return Reference(ReferenceKind.ORDINAL_BANDS, bands=biomarker.ordinal_bands)
    if sex is None:
        return NO_REFERENCE
    if sex is Sex.F:
        return bounded(biomarker.ref_min_f, biomarker.ref_max_f)
    return bounded(biomarker.ref_min_m, biomarker.ref_max_m)


def _band_of(value: Decimal, bands: list[dict[str, Any]]) -> dict[str, Any] | None:
    """`[min, max)` — lower limit inclusive, upper exclusive, null unbounded."""
    for band in bands:
        minimum, maximum = band.get("min"), band.get("max")
        if minimum is not None and value < Decimal(str(minimum)):
            continue
        if maximum is not None and value >= Decimal(str(maximum)):
            continue
        return band
    return None


def band_label(value: Decimal, reference: Reference) -> str | None:
    """The name of the band a value falls in, for the intervals that have names."""
    if reference.kind is not ReferenceKind.ORDINAL_BANDS or not reference.bands:
        return None
    band = _band_of(value, reference.bands)
    return None if band is None else band.get("label")


def compute_flag(value: Decimal, reference: Reference) -> ResultFlag | None:
    """None when no interval applies: an unclassified value beats a wrong flag."""
    if reference.kind is ReferenceKind.ORDINAL_BANDS:
        if not reference.bands:
            return None
        band = _band_of(value, reference.bands)
        flag = None if band is None else band.get("flag")
        return ResultFlag(flag) if flag in set(ResultFlag) else None
    if reference.minimum is None and reference.maximum is None:
        return None
    if reference.minimum is not None and value < reference.minimum:
        return ResultFlag.LOW
    if reference.maximum is not None and value > reference.maximum:
        return ResultFlag.HIGH
    return ResultFlag.NORMAL
