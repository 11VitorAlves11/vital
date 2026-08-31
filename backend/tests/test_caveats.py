"""Reasons to read a value with care — backlog 1.4 and 1.5.

A caveat never changes a flag or hides a number. It says the thing the reader
would otherwise have to hold in their head.
"""

from datetime import date, datetime, time
from decimal import Decimal

from app.models.biomarker import Biomarker
from app.models.enums import BiomarkerCategory, FastingState, ReferenceKind
from app.models.lab_report import LabReport, Result
from app.services import caveats
from app.services.caveats import CaveatCode

GLUCOSE = Biomarker(
    id=1,
    slug="glicose",
    name="Glicose",
    category=BiomarkerCategory.BIOQUIMICA,
    unit_default="mg/dL",
    canonical_unit="mg/dL",
    unit_conversions={},
    reference_kind=ReferenceKind.TWO_SIDED,
    fasting_sensitive=True,
    fasting_min_hours=8,
    time_sensitive=False,
    low_reliability_methods=[],
    aliases=["Glucose"],
)

IRON = Biomarker(
    id=2,
    slug="ferro-serico",
    name="Ferro sérico",
    category=BiomarkerCategory.FERRO,
    unit_default="µg/dL",
    canonical_unit="µg/dL",
    unit_conversions={},
    reference_kind=ReferenceKind.TWO_SIDED,
    fasting_sensitive=False,
    time_sensitive=True,
    time_window_start=time(7, 0),
    time_window_end=time(10, 0),
    low_reliability_methods=[],
    aliases=["Sideremia"],
)

CREATININE = Biomarker(
    id=3,
    slug="creatinina",
    name="Creatinina",
    category=BiomarkerCategory.RENAL,
    unit_default="mg/dL",
    canonical_unit="mg/dL",
    unit_conversions={},
    reference_kind=ReferenceKind.TWO_SIDED,
    fasting_sensitive=False,
    time_sensitive=False,
    low_reliability_methods=["Jaffe", "Picrato alcalino cinético"],
    aliases=["Creatinina sérica"],
)

HAEMOGLOBIN = Biomarker(
    id=4,
    slug="hemoglobina",
    name="Hemoglobina",
    category=BiomarkerCategory.HEMATOLOGIA,
    unit_default="g/dL",
    canonical_unit="g/dL",
    unit_conversions={},
    reference_kind=ReferenceKind.TWO_SIDED,
    fasting_sensitive=False,
    time_sensitive=False,
    low_reliability_methods=[],
    aliases=["Hb"],
)


def _report(**overrides: object) -> LabReport:
    fields: dict[str, object] = {
        "collected_on": date(2026, 3, 1),
        "collected_at": None,
        "lab_name": "Synlab",
        "fasting_state": FastingState.UNKNOWN,
        "fasting_hours": None,
    }
    fields.update(overrides)
    return LabReport(**fields)


def _result(biomarker: Biomarker, method: str | None = None) -> Result:
    result = Result(biomarker_id=biomarker.id, value=Decimal("1"), unit=biomarker.unit_default)
    result.biomarker = biomarker
    result.method = method
    return result


def _codes(result: Result, report: LabReport) -> list[CaveatCode]:
    return [caveat.code for caveat in caveats.for_result(result, report)]


def test_an_unrecorded_fast_is_only_raised_where_it_matters() -> None:
    """A non-fasted draw invalidates glucose and says nothing about haemoglobin."""
    report = _report()
    assert _codes(_result(GLUCOSE), report) == [CaveatCode.FASTING_UNKNOWN]
    assert _codes(_result(HAEMOGLOBIN), report) == []


def test_a_declared_meal_is_stated_outright() -> None:
    report = _report(fasting_state=FastingState.NOT_FASTING)
    assert _codes(_result(GLUCOSE), report) == [CaveatCode.NOT_FASTING]


def test_a_fast_that_was_long_enough_says_nothing() -> None:
    report = _report(fasting_state=FastingState.FASTING, fasting_hours=10)
    assert _codes(_result(GLUCOSE), report) == []


def test_a_fast_that_was_too_short_carries_both_numbers() -> None:
    report = _report(fasting_state=FastingState.FASTING, fasting_hours=5)
    [caveat] = caveats.for_result(_result(GLUCOSE), report)
    assert caveat.code is CaveatCode.FASTING_TOO_SHORT
    assert caveat.values == {"hours": "5", "required": "8"}


def test_a_fast_of_unstated_length_is_taken_at_its_word() -> None:
    """Someone who recorded that they fasted but not for how long is not accused
    of having eaten."""
    report = _report(fasting_state=FastingState.FASTING)
    assert _codes(_result(GLUCOSE), report) == []


def test_a_draw_inside_the_window_says_nothing() -> None:
    report = _report(collected_at=datetime(2026, 3, 1, 8, 30))
    assert _codes(_result(IRON), report) == []


def test_a_draw_outside_the_window_names_the_hour_and_the_window() -> None:
    report = _report(collected_at=datetime(2026, 3, 1, 16, 45))
    [caveat] = caveats.for_result(_result(IRON), report)
    assert caveat.code is CaveatCode.OUTSIDE_TIME_WINDOW
    assert caveat.values == {"time": "16:45", "start": "07:00", "end": "10:00"}


def test_a_missing_hour_is_raised_only_for_a_marker_that_needs_one() -> None:
    report = _report()
    assert _codes(_result(IRON), report) == [CaveatCode.COLLECTION_TIME_UNKNOWN]
    assert _codes(_result(GLUCOSE), report) == [CaveatCode.FASTING_UNKNOWN]


def test_a_known_low_reliability_assay_is_named() -> None:
    report = _report()
    [caveat] = caveats.for_result(_result(CREATININE, "picrato alcalino cinético"), report)
    assert caveat.code is CaveatCode.LOW_RELIABILITY_METHOD
    # Matched case-insensitively, reported as the laboratory wrote it.
    assert caveat.values == {"method": "picrato alcalino cinético"}


def test_an_ordinary_assay_is_not_flagged() -> None:
    assert _codes(_result(CREATININE, "enzimático"), _report()) == []


def test_a_change_of_method_marks_the_point_it_happened_on() -> None:
    report = _report()
    caveat = caveats.for_point(_result(CREATININE, "enzimático"), report, "Jaffe")[-1]
    assert caveat.code is CaveatCode.METHOD_CHANGED
    assert caveat.values == {"from": "Jaffe", "to": "enzimático"}


def test_the_first_point_of_a_series_has_nothing_to_differ_from() -> None:
    assert caveats.for_point(_result(CREATININE, "enzimático"), _report(), None) == []
