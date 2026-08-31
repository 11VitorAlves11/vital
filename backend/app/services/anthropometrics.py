"""Indices a weigh-in does not carry but height makes computable.

A scale reports kilograms. Almost every body-composition reference is defined on
a kilogram divided by the square of a height — BMI, FFMI, FMI — because raw mass
says nothing without the frame carrying it. Height lives on the profile, so the
scale cannot know these and the server can.

Derived values are computed on read rather than stored. A stored one would have
to be chased down and rewritten every time someone corrects their height, and it
would sit in the same table as a measurement, indistinguishable from one.
"""

from dataclasses import dataclass
from decimal import Decimal

#: The index a metric yields when divided by height squared.
INDEX_OF = {
    "weight": "bmi",
    "fat-free-mass": "ffmi",
    "fat-mass": "fmi",
}

# Whole-body skeletal muscle mass is deliberately absent. Dividing it by height
# squared looks like the ASMI that EWGSOP2 defines its 7.0/5.5 kg/m² cut-offs
# on, but ASMI is *appendicular* — arms and legs only, roughly three quarters of
# the whole-body figure a bioimpedance scale reports. Feeding one into the other
# would clear almost everyone of a low muscle mass they might actually have.


@dataclass(frozen=True, slots=True)
class Derived:
    """A value the server computed, and what it computed it from."""

    metric_slug: str
    value: Decimal
    #: The measured metric it came from, so the card can say where it is from.
    source_slug: str


def _index(mass_kg: Decimal, height_cm: Decimal) -> Decimal:
    """kg/m², to one decimal — the precision every published cut-off is quoted at."""
    height_m = height_cm / Decimal(100)
    return (mass_kg / (height_m * height_m)).quantize(Decimal("0.1"))


def derive(measured: dict[str, Decimal], height_cm: Decimal | None) -> list[Derived]:
    """Every index this weigh-in supports, given the height on the profile.

    Only for metrics the scale did not report itself: a device that computed its
    own BMI has the reader's real height in it, and ours is a profile field that
    may be older than the reading.
    """
    if height_cm is None or height_cm <= 0:
        return []

    return [
        Derived(metric_slug=index, value=_index(measured[mass], height_cm), source_slug=mass)
        for mass, index in INDEX_OF.items()
        if mass in measured and index not in measured
    ]
