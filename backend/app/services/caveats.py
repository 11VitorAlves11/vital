"""Reasons to read a number with care, attached to the number itself.

None of these change a flag or hide a value. They say what the reader would
otherwise have to remember: that this marker needed a fasted morning draw and
nobody recorded whether it was one, or that the assay changed between this
collection and the last, so the two points are not strictly comparable.

Each caveat is a code plus the values that go in the sentence. The wording lives
in the client's translations — the server has no business deciding which
language someone reads their own blood work in.
"""

from dataclasses import dataclass, field
from datetime import date, time
from enum import StrEnum

from app.models.biomarker import Biomarker
from app.models.enums import FastingState
from app.models.lab_report import LabReport, Result


class CaveatCode(StrEnum):
    FASTING_UNKNOWN = "fasting_unknown"
    NOT_FASTING = "not_fasting"
    FASTING_TOO_SHORT = "fasting_too_short"
    COLLECTION_TIME_UNKNOWN = "collection_time_unknown"
    OUTSIDE_TIME_WINDOW = "outside_time_window"
    LOW_RELIABILITY_METHOD = "low_reliability_method"
    METHOD_CHANGED = "method_changed"
    # Only a comparison between two collections can raise these two: one draw on
    # its own has nothing to be incomparable with.
    REFERENCE_CHANGED = "reference_changed"
    UNITS_INCOMPARABLE = "units_incomparable"
    SEASONAL_MARKER = "seasonal_marker"


#: Below this, two draws are "the same part of the year" and not worth flagging.
SEASONAL_GAP_MONTHS = 2


@dataclass(frozen=True, slots=True)
class Caveat:
    code: CaveatCode
    #: Interpolated into the translated sentence; stringified for the wire.
    values: dict[str, str] = field(default_factory=dict)


def _hhmm(moment: time) -> str:
    return moment.strftime("%H:%M")


def _fasting_caveats(biomarker: Biomarker, report: LabReport) -> list[Caveat]:
    if not biomarker.fasting_sensitive:
        return []
    if report.fasting_state is FastingState.UNKNOWN:
        return [Caveat(CaveatCode.FASTING_UNKNOWN)]
    if report.fasting_state is FastingState.NOT_FASTING:
        return [Caveat(CaveatCode.NOT_FASTING)]

    required = biomarker.fasting_min_hours
    if required is None or report.fasting_hours is None or report.fasting_hours >= required:
        return []
    return [
        Caveat(
            CaveatCode.FASTING_TOO_SHORT,
            {"hours": str(report.fasting_hours), "required": str(required)},
        )
    ]


def _timing_caveats(biomarker: Biomarker, report: LabReport) -> list[Caveat]:
    if not biomarker.time_sensitive:
        return []
    start, end = biomarker.time_window_start, biomarker.time_window_end
    if report.collected_at is None:
        # Only worth saying when there is a window to have missed.
        if start is None or end is None:
            return []
        return [
            Caveat(
                CaveatCode.COLLECTION_TIME_UNKNOWN,
                {"start": _hhmm(start), "end": _hhmm(end)},
            )
        ]

    drawn = report.collected_at.time()
    if start is None or end is None or start <= drawn <= end:
        return []
    return [
        Caveat(
            CaveatCode.OUTSIDE_TIME_WINDOW,
            {"time": _hhmm(drawn), "start": _hhmm(start), "end": _hhmm(end)},
        )
    ]


def _method_caveats(biomarker: Biomarker, result: Result) -> list[Caveat]:
    if result.method is None:
        return []
    known = {method.casefold() for method in biomarker.low_reliability_methods}
    if result.method.casefold() not in known:
        return []
    return [Caveat(CaveatCode.LOW_RELIABILITY_METHOD, {"method": result.method})]


def _months_apart(a: date, b: date) -> int:
    """Distance around the calendar year between two dates' months — 0 for the
    same month, 6 for opposite sides of the year. The year itself does not
    matter: a January draw and a December draw a year later are 1 month apart.
    """
    diff = abs(a.month - b.month)
    return min(diff, 12 - diff)


def seasonal_caveat(biomarker: Biomarker, previous: date, current: date) -> Caveat | None:
    """Two draws far apart in the calendar, for a marker that moves with it.

    Never says which direction: the app has no hemisphere to reason from, only
    that the gap itself may explain part of what changed.
    """
    if not biomarker.seasonal:
        return None
    gap = _months_apart(previous, current)
    if gap < SEASONAL_GAP_MONTHS:
        return None
    return Caveat(CaveatCode.SEASONAL_MARKER, {"months_apart": str(gap)})


def for_result(result: Result, report: LabReport) -> list[Caveat]:
    """Everything worth knowing about this one reading, in isolation."""
    biomarker = result.biomarker
    return [
        *_fasting_caveats(biomarker, report),
        *_timing_caveats(biomarker, report),
        *_method_caveats(biomarker, result),
    ]


def for_point(
    result: Result,
    report: LabReport,
    previous_method: str | None,
    previous_collected_on: date | None = None,
) -> list[Caveat]:
    """The same, plus what only the series can see.

    A change of method between two draws is a discontinuity in the line: the
    difference between the points may be the assay rather than the body. A gap
    in the calendar is the same idea for a marker that moves with the seasons.
    """
    caveats = for_result(result, report)
    if (
        result.method is not None
        and previous_method is not None
        and result.method.casefold() != previous_method.casefold()
    ):
        caveats.append(
            Caveat(CaveatCode.METHOD_CHANGED, {"from": previous_method, "to": result.method})
        )
    if previous_collected_on is not None:
        seasonal = seasonal_caveat(result.biomarker, previous_collected_on, report.collected_on)
        if seasonal is not None:
            caveats.append(seasonal)
    return caveats
