"""Clinical classification of body-composition values.

The scale's own rating is never stored or shown: it is proprietary, inconsistent
between brands, and occasionally contradicts itself. Every flag is recomputed here
from the catalogue bands, which carry their standard's provenance.
"""

from decimal import Decimal
from typing import Any

from app.models.body import BodyMetric
from app.models.enums import Sex


def bands_for(metric: BodyMetric, sex: Sex | None) -> list[dict[str, Any]] | None:
    """The band set that applies to this user, or None when none does.

    Trend-only metrics have no bands at all; an unknown sex means we decline to
    guess which set to apply rather than defaulting to one.
    """
    if sex is None:
        return None
    return metric.bands_f if sex is Sex.F else metric.bands_m


def age_band_for(
    metric: BodyMetric, sex: Sex | None, age_years: int | None
) -> list[dict[str, Any]] | None:
    """The age-partitioned band set for this reading, or None when the metric
    has no such reference, the sex or birth date is unknown, or this age falls
    outside every bracket the reference actually covers.

    A gap between brackets is not filled by the nearest one: a reference that
    studied ages 20–79 has nothing to say about 85, and guessing would lend a
    number authority the source never gave it.
    """
    if sex is None or age_years is None:
        return None
    brackets = metric.age_bands_f if sex is Sex.F else metric.age_bands_m
    if brackets is None:
        return None
    for bracket in brackets:
        minimum, maximum = bracket["age_min"], bracket["age_max"]
        if age_years >= minimum and (maximum is None or age_years < maximum):
            bands: list[dict[str, Any]] = bracket["bands"]
            return bands
    return None


def _matches(value: Decimal, band: dict[str, Any]) -> bool:
    """`[min, max)` — lower limit inclusive, upper exclusive, null unbounded."""
    minimum, maximum = band.get("min"), band.get("max")
    if minimum is not None and value < Decimal(str(minimum)):
        return False
    return not (maximum is not None and value >= Decimal(str(maximum)))


def classify(value: Decimal, bands: list[dict[str, Any]] | None) -> tuple[str | None, str | None]:
    """Return (flag, label) for a value, or (None, None) when it cannot be classified."""
    if not bands:
        return None, None
    for band in bands:
        if _matches(value, band):
            return band.get("flag"), band.get("label")
    return None, None
