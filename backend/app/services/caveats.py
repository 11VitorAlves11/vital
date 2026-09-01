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
from datetime import time
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


def for_result(result: Result, report: LabReport) -> list[Caveat]:
    """Everything worth knowing about this one reading, in isolation."""
    biomarker = result.biomarker
    return [
        *_fasting_caveats(biomarker, report),
        *_timing_caveats(biomarker, report),
        *_method_caveats(biomarker, result),
    ]


def for_point(result: Result, report: LabReport, previous_method: str | None) -> list[Caveat]:
    """The same, plus what only the series can see.

    A change of method between two draws is a discontinuity in the line: the
    difference between the points may be the assay rather than the body.
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
    return caveats
