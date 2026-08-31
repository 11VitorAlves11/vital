"""Conversion of a reported value into the catalogue's canonical unit.

Laboratories report the same marker in different units — B12 in pg/mL or pmol/L,
vitamin D in ng/mL or nmol/L — and a chart that plots both as raw numbers shows a
cliff where there was only a change of supplier. The reported value is never
touched; the canonical one is derived alongside it, and is what a series is drawn
from once every point has one.

A unit the catalogue has no factor for converts to nothing at all. Guessing that
"mcg/dL" means "µg/dL" is the kind of assumption that silently multiplies a
result by ten.
"""

import re
from decimal import Decimal

from app.models.biomarker import Biomarker

#: value × factor = canonical value, with the unit as reported.
Conversion = tuple[Decimal | None, str | None, Decimal | None]

_ONE = Decimal(1)
#: `u` as an ASCII stand-in for `µ`, but only where it can only mean micro —
#: never in `U/L` or `UI/mL`, where a `u` is an enzyme or international unit.
_ASCII_MICRO = re.compile(r"(?<![a-z0-9])u(?=g|mol|l(?![a-z]))")


def normalise_unit(unit: str) -> str:
    """Fold the spelling differences that are notation, not meaning.

    Whitespace and case vary freely between reports, and `μ` (Greek mu), `u` and
    `µ` (micro sign) are written interchangeably. Everything else — including
    `mg` against `µg` — is a real difference and survives untouched.
    """
    folded = re.sub(r"\s+", "", unit).casefold().replace("μ", "µ")
    return _ASCII_MICRO.sub("µ", folded)


def to_canonical(biomarker: Biomarker, value: Decimal, unit: str | None) -> Conversion:
    """`(canonical_value, canonical_unit, factor)`, or all-None when unconvertible."""
    reported = normalise_unit(unit) if unit else normalise_unit(biomarker.canonical_unit)
    if reported == normalise_unit(biomarker.canonical_unit):
        return value, biomarker.canonical_unit, _ONE

    factors = {
        normalise_unit(key): factor for key, factor in (biomarker.unit_conversions or {}).items()
    }
    factor = factors.get(reported)
    if factor is None:
        return None, None, None

    # Through str so a factor written 0.4006 in the seed stays 0.4006, rather
    # than the nearest binary float, before it multiplies someone's result.
    exact = Decimal(str(factor))
    return value * exact, biomarker.canonical_unit, exact


def convert_bound(bound: Decimal | None, factor: Decimal | None) -> Decimal | None:
    """A reference limit follows its value into the canonical unit, or nowhere."""
    if bound is None or factor is None:
        return None
    return bound * factor
