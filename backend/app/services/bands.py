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
