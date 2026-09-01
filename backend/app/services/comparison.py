"""Two collections read against each other, marker by marker.

A chart needs three or four points before its shape means anything. With two
collections there is no shape — only a list of differences — and reading them off
a line is harder than reading them from a column of numbers.

Everything here is arithmetic on one scale. Two readings of the same marker are
only subtractable once they are in the same unit, and a laboratory that reports
B12 in pmol/L where the last one used ng/L would otherwise show a fall of
several hundred that never happened. When no common scale exists the difference
is simply not computed: an absent delta is honest, a wrong one is not.

Nothing here re-flags anything. The flag on each side is the one that was
computed when the value was written, against the interval that report carried.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.models.biomarker import Biomarker
from app.models.enums import BiomarkerCategory, ReferenceKind
from app.models.lab_report import LabReport, Result
from app.services.caveats import Caveat, CaveatCode
from app.services.units import convert_bound, normalise_unit

_HUNDRED = Decimal(100)
#: Two decimals on a percentage. Beyond that it is the division showing through,
#: not a difference anybody measured.
_PERCENT_STEP = Decimal("0.01")

#: The catalogue's own order, so a comparison lists panels the way every other
#: view does rather than alphabetically by the enum's spelling.
_CATEGORY_ORDER = {category: index for index, category in enumerate(BiomarkerCategory)}


@dataclass(frozen=True, slots=True)
class Reading:
    """One result placed on a chosen scale — the value and its bounds together.

    The bounds travel with the value because they have to move with it: a range
    of 13–17 ng/L means nothing next to a value converted into pmol/L.
    """

    value: Decimal
    minimum: Decimal | None
    maximum: Decimal | None
    unit: str


@dataclass(frozen=True, slots=True)
class Comparison:
    """What changed for one biomarker between the two collections.

    Either side may be missing: a marker measured once and not the next time is
    part of what a comparison has to show, not a row to drop.
    """

    biomarker: Biomarker
    previous: Result | None
    current: Result | None
    #: In `unit`, the scale both sides were put on. None when there was no common one.
    delta: Decimal | None
    #: Against the earlier value. None when it was zero, or when delta is.
    percent_change: Decimal | None
    unit: str | None
    caveats: list[Caveat]


def _canonical(result: Result) -> Reading | None:
    """The reading in the catalogue's unit, when it was convertible at all."""
    if result.canonical_value is None or result.canonical_unit is None:
        return None
    return Reading(
        result.canonical_value,
        convert_bound(result.ref_min, result.conversion_factor),
        convert_bound(result.ref_max, result.conversion_factor),
        result.canonical_unit,
    )


def _reported(result: Result) -> Reading:
    """The reading as the laboratory printed it, in its own unit."""
    return Reading(result.value, result.ref_min, result.ref_max, result.unit)


def _on_one_scale(previous: Result, current: Result) -> tuple[Reading, Reading] | None:
    """Both readings in a single unit, or None when they cannot share one."""
    before, after = _canonical(previous), _canonical(current)
    if before is not None and after is not None and before.unit == after.unit:
        return before, after
    # Neither converted, but both were reported the same way. Subtracting them is
    # still arithmetic on one scale, even where the catalogue has no factor for it.
    if normalise_unit(previous.unit) == normalise_unit(current.unit):
        return _reported(previous), _reported(current)
    return None


def _reference_moved(previous: Reading, current: Reading, kinds: set[ReferenceKind]) -> bool:
    """Whether the interval itself changed under the two values.

    Ordinal scales are exempt: those bands are the catalogue's clinical consensus,
    identical on both sides by construction, and the numbers a report prints
    beside them do not classify anything (see DT5).
    """
    if kinds == {ReferenceKind.ORDINAL_BANDS}:
        return False
    return previous.minimum != current.minimum or previous.maximum != current.maximum


def _method_changed(previous: Result, current: Result) -> bool:
    return (
        previous.method is not None
        and current.method is not None
        and previous.method.casefold() != current.method.casefold()
    )


def _difference(
    previous: Result, current: Result
) -> tuple[Decimal | None, Decimal | None, str | None, list[Caveat]]:
    caveats: list[Caveat] = []
    if _method_changed(previous, current):
        caveats.append(
            Caveat(
                CaveatCode.METHOD_CHANGED,
                {"from": previous.method or "", "to": current.method or ""},
            )
        )

    scale = _on_one_scale(previous, current)
    if scale is None:
        caveats.append(
            Caveat(CaveatCode.UNITS_INCOMPARABLE, {"from": previous.unit, "to": current.unit})
        )
        return None, None, None, caveats

    before, after = scale
    if _reference_moved(before, after, {previous.reference_kind, current.reference_kind}):
        caveats.append(Caveat(CaveatCode.REFERENCE_CHANGED))

    delta = after.value - before.value
    percent = (
        None
        if before.value == 0
        else (delta / before.value * _HUNDRED).quantize(_PERCENT_STEP, rounding=ROUND_HALF_UP)
    )
    return delta, percent, after.unit, caveats


def compare(previous: LabReport, current: LabReport) -> list[Comparison]:
    """Every marker either collection measured, in catalogue order.

    `previous` is the earlier draw: a delta reads forward in time regardless of
    the order the two reports were asked for.
    """
    before = {result.biomarker_id: result for result in previous.results}
    after = {result.biomarker_id: result for result in current.results}
    # Named once from either side: a marker missing from one collection still has
    # a catalogue entry, and it comes from whichever report did measure it.
    markers = {
        result.biomarker_id: result.biomarker for result in (*previous.results, *current.results)
    }

    rows = []
    for biomarker_id in before.keys() | after.keys():
        earlier, later = before.get(biomarker_id), after.get(biomarker_id)
        delta, percent, unit, caveats = (
            _difference(earlier, later)
            if earlier is not None and later is not None
            else (None, None, None, [])
        )
        rows.append(
            Comparison(
                biomarker=markers[biomarker_id],
                previous=earlier,
                current=later,
                delta=delta,
                percent_change=percent,
                unit=unit,
                caveats=caveats,
            )
        )

    return sorted(
        rows, key=lambda row: (_CATEGORY_ORDER[row.biomarker.category], row.biomarker.name)
    )
